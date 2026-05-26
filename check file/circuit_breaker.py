"""
circuit_breaker.py
==================
Daily loss circuit breaker + over-trading guard for live_trader.py

Protects capital by:
  1. Shutting down trading if daily loss exceeds a set % of capital
  2. Enforcing cooldown periods between trades
  3. Blocking trades during high-impact news windows
  4. Logging every decision with a reason code

Usage:
    from circuit_breaker import CircuitBreaker, BreakerConfig

    cb = CircuitBreaker(capital=10_000, config=BreakerConfig())

    # Before every trade attempt:
    ok, reason = cb.allow_trade()
    if not ok:
        print(f"Trade blocked: {reason}")
        continue

    # After a trade closes:
    cb.record_trade(pnl=-120.00)   # negative = loss, positive = win

    # End of day reset:
    cb.reset_day()

    # Full status:
    print(cb.status())
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Tuple


# ─────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────

@dataclass
class BreakerConfig:
    # ── Daily loss limits ──────────────────────
    max_daily_loss_pct  : float = 3.0    # % of capital → hard shutdown
    warn_daily_loss_pct : float = 2.0    # % of capital → warning (trades still allowed)
    max_daily_trades    : int   = 8      # hard cap on number of trades per day

    # ── Cooldown periods (seconds) ─────────────
    cooldown_after_loss   : int = 600    # 10 min after any losing trade
    cooldown_after_win    : int = 300    # 5 min after a winning trade
    cooldown_regime_switch: int = 300    # 5 min after regime change

    # ── News blackout (minutes before/after) ───
    news_blackout_minutes : int = 5

    # ── High-impact news events (UTC HH:MM) ────
    # Add/remove times to match your economic calendar
    news_events_utc: List[str] = field(default_factory=lambda: [
        "08:30",  # UK data (CPI, GDP, etc.)
        "13:30",  # US data (CPI, NFP, Retail Sales)
        "14:00",  # US ISM / JOLTS
        "18:00",  # Fed rate decisions / FOMC
        "18:30",  # Fed press conference start
    ])

    # ── Trading session windows (UTC) ──────────
    allowed_sessions: List[Tuple[str, str]] = field(default_factory=lambda: [
        ("08:00", "11:00"),   # London
        ("13:00", "16:00"),   # New York
    ])


# ─────────────────────────────────────────────
#  Circuit Breaker
# ─────────────────────────────────────────────

class CircuitBreaker:
    """
    Pre-trade gate that enforces all risk management rules.

    Parameters
    ----------
    capital : float        Current account capital in USD
    config  : BreakerConfig
    """

    def __init__(self, capital: float, config: BreakerConfig = None):
        self.capital      = capital
        self.cfg          = config or BreakerConfig()

        # ── Daily state ────────────────────────
        self.daily_pnl    : float = 0.0
        self.daily_trades : int   = 0
        self.trade_log    : List[dict] = []

        # ── Cooldown state ─────────────────────
        self._last_trade_close_ts : float = 0.0
        self._last_trade_was_loss : bool  = False
        self._regime_switch_ts    : float = 0.0

        # ── Circuit state ──────────────────────
        self.tripped      : bool  = False
        self.trip_reason  : str   = ""

    # ─────────────────────────────────────────
    #  Main gate — call before every trade
    # ─────────────────────────────────────────

    def allow_trade(self) -> Tuple[bool, str]:
        """
        Returns (True, "OK") if the trade is allowed.
        Returns (False, reason_str) if it should be blocked.

        Check these in order — first failure blocks the trade.
        """

        # 1. Hard circuit trip
        if self.tripped:
            return False, f"CIRCUIT_TRIPPED: {self.trip_reason}"

        # 2. Daily loss limit
        loss_pct = abs(self.daily_pnl) / self.capital * 100
        if self.daily_pnl < 0 and loss_pct >= self.cfg.max_daily_loss_pct:
            self._trip(f"Daily loss limit hit: -{loss_pct:.1f}% of capital")
            return False, self.trip_reason

        # 3. Daily trade count
        if self.daily_trades >= self.cfg.max_daily_trades:
            return False, f"MAX_TRADES_REACHED: {self.daily_trades} trades today"

        # 4. Session window
        if not self._in_session():
            return False, f"OUTSIDE_SESSION: current UTC time not in allowed windows"

        # 5. News blackout
        blocked, news_reason = self._in_news_blackout()
        if blocked:
            return False, f"NEWS_BLACKOUT: {news_reason}"

        # 6. Cooldown after trade
        cooldown_ok, cd_reason = self._cooldown_clear()
        if not cooldown_ok:
            return False, cd_reason

        # 7. Regime switch cooldown
        elapsed_regime = time.time() - self._regime_switch_ts
        if elapsed_regime < self.cfg.cooldown_regime_switch:
            remaining = int(self.cfg.cooldown_regime_switch - elapsed_regime)
            return False, f"REGIME_COOLDOWN: {remaining}s remaining"

        # 8. Warning zone (daily loss between warn% and max%)
        if self.daily_pnl < 0 and loss_pct >= self.cfg.warn_daily_loss_pct:
            # Still allowed but caller should log the warning
            return True, f"WARN_DAILY_LOSS_{loss_pct:.1f}PCT"

        return True, "OK"

    # ─────────────────────────────────────────
    #  Record a closed trade
    # ─────────────────────────────────────────

    def record_trade(self, pnl: float, notes: str = ""):
        """Call this after every trade closes."""
        self.daily_pnl          += pnl
        self.daily_trades       += 1
        self._last_trade_close_ts = time.time()
        self._last_trade_was_loss = pnl < 0

        self.trade_log.append({
            "time"       : _now_utc(),
            "pnl"        : round(pnl, 2),
            "daily_pnl"  : round(self.daily_pnl, 2),
            "trade_num"  : self.daily_trades,
            "notes"      : notes,
        })

        # Check if the loss just crossed the hard limit
        loss_pct = abs(self.daily_pnl) / self.capital * 100
        if self.daily_pnl < 0 and loss_pct >= self.cfg.max_daily_loss_pct:
            self._trip(f"Daily loss {loss_pct:.1f}% exceeded {self.cfg.max_daily_loss_pct}% limit")

    # ─────────────────────────────────────────
    #  Notify of a regime change
    # ─────────────────────────────────────────

    def notify_regime_change(self, old_regime: str, new_regime: str):
        """Call from your regime detector when regime flips."""
        self._regime_switch_ts = time.time()
        self.trade_log.append({
            "time"  : _now_utc(),
            "event" : f"REGIME_CHANGE: {old_regime} → {new_regime}",
        })

    # ─────────────────────────────────────────
    #  End-of-day reset
    # ─────────────────────────────────────────

    def reset_day(self):
        """Call at the start of each new trading day (e.g. 00:00 UTC)."""
        self.daily_pnl    = 0.0
        self.daily_trades = 0
        self.tripped      = False
        self.trip_reason  = ""
        self.trade_log.append({"time": _now_utc(), "event": "DAY_RESET"})

    # ─────────────────────────────────────────
    #  Status snapshot
    # ─────────────────────────────────────────

    def status(self) -> dict:
        loss_pct     = abs(self.daily_pnl) / self.capital * 100 if self.daily_pnl < 0 else 0
        can_trade, reason = self.allow_trade()
        cd_remaining = self._cooldown_remaining()

        return {
            "can_trade"          : can_trade,
            "block_reason"       : reason,
            "circuit_tripped"    : self.tripped,
            "trip_reason"        : self.trip_reason,
            "daily_pnl_usd"      : round(self.daily_pnl, 2),
            "daily_loss_pct"     : round(loss_pct, 2),
            "daily_trades"       : self.daily_trades,
            "max_daily_trades"   : self.cfg.max_daily_trades,
            "cooldown_remaining_s": cd_remaining,
            "in_session"         : self._in_session(),
            "in_news_blackout"   : self._in_news_blackout()[0],
            "utc_now"            : _now_utc(),
        }

    # ─────────────────────────────────────────
    #  Private helpers
    # ─────────────────────────────────────────

    def _trip(self, reason: str):
        self.tripped     = True
        self.trip_reason = reason
        self.trade_log.append({"time": _now_utc(), "event": f"CIRCUIT_TRIPPED: {reason}"})

    def _cooldown_clear(self) -> Tuple[bool, str]:
        if self._last_trade_close_ts == 0:
            return True, "OK"
        elapsed  = time.time() - self._last_trade_close_ts
        required = (
            self.cfg.cooldown_after_loss if self._last_trade_was_loss
            else self.cfg.cooldown_after_win
        )
        if elapsed < required:
            label     = "LOSS_COOLDOWN" if self._last_trade_was_loss else "WIN_COOLDOWN"
            remaining = int(required - elapsed)
            return False, f"{label}: {remaining}s remaining"
        return True, "OK"

    def _cooldown_remaining(self) -> int:
        if self._last_trade_close_ts == 0:
            return 0
        elapsed  = time.time() - self._last_trade_close_ts
        required = (
            self.cfg.cooldown_after_loss if self._last_trade_was_loss
            else self.cfg.cooldown_after_win
        )
        return max(0, int(required - elapsed))

    def _in_session(self) -> bool:
        now = datetime.now(timezone.utc)
        t   = now.strftime("%H:%M")
        for start, end in self.cfg.allowed_sessions:
            if start <= t <= end:
                return True
        return False

    def _in_news_blackout(self) -> Tuple[bool, str]:
        now     = datetime.now(timezone.utc)
        t_now   = now.strftime("%H:%M")
        margin  = timedelta(minutes=self.cfg.news_blackout_minutes)

        for event_time_str in self.cfg.news_events_utc:
            h, m   = map(int, event_time_str.split(":"))
            event  = now.replace(hour=h, minute=m, second=0, microsecond=0)
            window_start = (event - margin).strftime("%H:%M")
            window_end   = (event + margin).strftime("%H:%M")
            if window_start <= t_now <= window_end:
                return True, f"near {event_time_str} UTC event"

        return False, ""


# ─────────────────────────────────────────────
#  Helper
# ─────────────────────────────────────────────

def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ─────────────────────────────────────────────
#  Smoke test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Circuit Breaker Simulation ===\n")

    cb = CircuitBreaker(capital=10_000)

    # Simulate a sequence of trades
    scenarios = [
        ("Trade 1 — win $120",   120.0),
        ("Trade 2 — loss $-85",  -85.0),
        ("Trade 3 — loss $-95",  -95.0),
        ("Trade 4 — loss $-140", -140.0),
        ("Trade 5 — loss $-200", -200.0),   # cumulative loss now -$520
        ("Trade 6 — loss $-310", -310.0),   # crosses 3% → $300 limit
    ]

    for label, pnl in scenarios:
        can, reason = cb.allow_trade()
        print(f"  {label}")
        print(f"    allow_trade() → {can}  |  {reason}")
        if can or "COOLDOWN" in reason or "SESSION" in reason or "NEWS" in reason:
            cb.record_trade(pnl)
            # skip cooldown for simulation
            cb._last_trade_close_ts = 0
        print(f"    daily_pnl=${cb.daily_pnl:.2f}  trades={cb.daily_trades}\n")

    print("\n--- Final Status ---")
    for k, v in cb.status().items():
        print(f"  {k:<28} {v}")
