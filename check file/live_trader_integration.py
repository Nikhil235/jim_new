"""
live_trader_integration.py
==========================
Shows exactly WHERE and HOW to plug trailing_stop.py and circuit_breaker.py
into your existing live_trader.py loop.

This is a template — paste the relevant sections into your live file.
"""

from trailing_stop  import TrailingStop, TrailingConfig
from circuit_breaker import CircuitBreaker, BreakerConfig
from adx_regime_detector import RegimeDetector

# ── One-time setup at bot startup ──────────────────────────────────────────

cb = CircuitBreaker(
    capital = 10_000,
    config  = BreakerConfig(
        max_daily_loss_pct   = 3.0,   # shutdown if day-loss > 3%
        warn_daily_loss_pct  = 2.0,   # warn at 2%
        max_daily_trades     = 8,
        cooldown_after_loss  = 600,   # 10 min
        cooldown_after_win   = 300,   # 5 min
        cooldown_regime_switch = 300, # 5 min after regime flip
    )
)

open_trade_stop : TrailingStop | None = None   # one active stop at a time
current_regime  : str = "UNKNOWN"


# ── Main trading loop  (runs every bar / tick) ─────────────────────────────

def on_new_bar(df, ai_signal, ai_confidence, atr_value, current_price):
    """
    Drop-in replacement for your existing bar-handler in live_trader.py

    Parameters
    ----------
    df              : latest OHLCV DataFrame (200+ rows)
    ai_signal       : "LONG" | "SHORT" | "NONE"  from your ensemble model
    ai_confidence   : float  0.0–1.0
    atr_value       : float  current 14-period ATR
    current_price   : float  latest close price
    """
    global open_trade_stop, current_regime

    # ── 1. Detect regime & notify breaker if it changed ───────────────────
    detector   = RegimeDetector(df)
    new_regime = detector.detect()

    if new_regime != current_regime and current_regime != "UNKNOWN":
        print(f"[REGIME] {current_regime} → {new_regime}")
        cb.notify_regime_change(current_regime, new_regime)

    current_regime = new_regime

    # ── 2. Update trailing stop if a trade is open ─────────────────────────
    if open_trade_stop is not None:
        action = open_trade_stop.update(current_price)
        print(f"[STOP]  price={current_price}  stop={open_trade_stop.current_stop}  action={action}")

        if action == "STOP_HIT":
            # Calculate P&L and record it
            entry = open_trade_stop.entry_price
            if open_trade_stop.direction == "LONG":
                pnl = (open_trade_stop.current_stop - entry) * 1.0   # × lot size
            else:
                pnl = (entry - open_trade_stop.current_stop) * 1.0

            print(f"[TRADE CLOSED]  reason=STOP_HIT  pnl=${pnl:.2f}")
            cb.record_trade(pnl, notes="trailing stop hit")
            open_trade_stop = None
            return   # don't open a new trade on the same bar

        elif action == "MOVE_STOP":
            print(f"[STOP MOVED]  new_stop={open_trade_stop.current_stop}")

        elif action == "BREAKEVEN":
            print(f"[BREAKEVEN SET]  stop locked at entry {open_trade_stop.entry_price}")

        # Trade still open — don't open another
        return

    # ── 3. Gate every new entry through the circuit breaker ───────────────
    can_trade, reason = cb.allow_trade()

    if not can_trade:
        print(f"[BLOCKED]  {reason}")
        return

    if reason.startswith("WARN"):
        print(f"[WARNING]  {reason} — trading with reduced size")
        # optionally: halve position size here

    # ── 4. Check AI signal ─────────────────────────────────────────────────
    if ai_signal == "NONE" or ai_confidence < 0.55:
        print(f"[NO SIGNAL]  confidence={ai_confidence:.2f}")
        return

    # ── 5. Apply regime filter ─────────────────────────────────────────────
    pos_mult = detector.position_multiplier()
    if pos_mult == 0.0:
        print(f"[REGIME BLOCK]  regime={new_regime}  no trend trades in ranging market")
        return

    # ── 6. Open trade + attach trailing stop ──────────────────────────────
    entry_price = current_price   # in live: use actual fill price

    open_trade_stop = TrailingStop(
        direction   = ai_signal,
        entry_price = entry_price,
        atr         = atr_value,
        config      = TrailingConfig(
            atr_stop_mult    = 1.5,
            atr_trail_mult   = 1.2,
            activation_mult  = 1.0,
            breakeven_mult   = 0.5,
            enable_breakeven = True,
        )
    )

    print(
        f"[TRADE OPEN]  {ai_signal}  entry={entry_price}  "
        f"stop={open_trade_stop.current_stop}  "
        f"target={entry_price + (1.5 * atr_value * 2):.2f}  "
        f"regime={new_regime}  conf={ai_confidence:.2f}"
    )


# ── End-of-day reset  (schedule this at 00:00 UTC) ─────────────────────────

def on_day_end():
    """Call once per day at market close / midnight UTC."""
    print(f"\n[DAY END]  Daily P&L: ${cb.daily_pnl:.2f}  Trades: {cb.daily_trades}")
    cb.reset_day()
    print("[DAY RESET]  Circuit breaker cleared for new session\n")


# ── Status check  (call anytime to inspect system state) ───────────────────

def print_system_status():
    print("\n=== System Status ===")
    for k, v in cb.status().items():
        print(f"  {k:<28} {v}")
    if open_trade_stop:
        print("\n=== Open Trade Stop ===")
        for k, v in open_trade_stop.status().items():
            print(f"  {k:<28} {v}")
    print()


# ─────────────────────────────────────────────
#  Demo run
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import pandas as pd, numpy as np

    np.random.seed(1)
    n     = 300
    close = 4500 + np.cumsum(np.random.randn(n) * 6)
    df    = pd.DataFrame({
        "open"  : close - np.abs(np.random.randn(n) * 2),
        "high"  : close + np.abs(np.random.randn(n) * 5),
        "low"   : close - np.abs(np.random.randn(n) * 5),
        "close" : close,
        "volume": np.random.randint(200, 800, n),
    })

    atr = float(df["high"].sub(df["low"]).rolling(14).mean().iloc[-1])

    print("── Simulating 5 bars ──\n")
    bar_signals = [
        ("LONG",  0.72, close[-1]),
        ("LONG",  0.72, close[-1] + 5),
        ("LONG",  0.72, close[-1] + 10),
        ("LONG",  0.72, close[-1] - 3),
        ("LONG",  0.72, close[-1] - 12),   # stop should hit here
    ]

    # Bypass session/time checks for demo
    cb.cfg.allowed_sessions = [("00:00", "23:59")]
    cb.cfg.news_events_utc  = []

    for sig, conf, price in bar_signals:
        print(f"\n--- bar  price={price:.2f} ---")
        on_new_bar(df, sig, conf, atr, price)

    print_system_status()
