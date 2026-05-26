"""
trailing_stop.py
================
ATR-based trailing stop manager — drop-in for live_trader.py

How it works:
    - Entry: stop is placed 1.5×ATR below entry (LONG) or above (SHORT)
    - Once price moves 1×ATR in your favour → stop trails behind price
    - Stop only ever moves in the profitable direction — never backwards
    - Optional breakeven lock: once +0.5×ATR profit, stop moves to entry

Usage:
    from trailing_stop import TrailingStop

    ts = TrailingStop(
        direction   = "LONG",
        entry_price = 4561.00,
        atr         = 8.50,
    )

    # On every new price tick / bar close:
    action = ts.update(current_price=4575.00)
    # action → "HOLD" | "MOVE_STOP" | "STOP_HIT"

    print(ts.current_stop)   # current stop level
    print(ts.status())       # full snapshot dict
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
import time


# ─────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────

@dataclass
class TrailingConfig:
    atr_stop_mult      : float = 1.5   # initial stop distance in ATR units
    atr_trail_mult     : float = 1.2   # trailing distance once activated
    activation_mult    : float = 1.0   # profit in ATR units before trail starts
    breakeven_mult     : float = 0.5   # profit in ATR units to lock breakeven
    enable_breakeven   : bool  = True  # move stop to entry once in profit


# ─────────────────────────────────────────────
#  Trailing Stop
# ─────────────────────────────────────────────

class TrailingStop:
    """
    Manages a single trade's stop loss with ATR-based trailing logic.

    Parameters
    ----------
    direction   : "LONG" or "SHORT"
    entry_price : Fill price of the trade
    atr         : ATR value at entry (use 14-period ATR on your timeframe)
    config      : TrailingConfig (optional — uses sensible defaults)
    """

    def __init__(
        self,
        direction   : Literal["LONG", "SHORT"],
        entry_price : float,
        atr         : float,
        config      : TrailingConfig = None,
    ):
        self.direction   = direction
        self.entry_price = entry_price
        self.atr         = atr
        self.cfg         = config or TrailingConfig()

        # State
        self.initial_stop   : float = self._calc_initial_stop()
        self.current_stop   : float = self.initial_stop
        self.highest_price  : float = entry_price   # for LONG
        self.lowest_price   : float = entry_price   # for SHORT
        self.trailing_active: bool  = False
        self.breakeven_set  : bool  = False
        self.is_closed      : bool  = False
        self.close_reason   : str   = ""
        self.open_time      : float = time.time()

        # History log
        self.stop_history: list[dict] = [
            {"event": "ENTRY", "stop": self.initial_stop, "price": entry_price}
        ]

    # ── Initial stop calculation ─────────────────
    def _calc_initial_stop(self) -> float:
        dist = self.cfg.atr_stop_mult * self.atr
        if self.direction == "LONG":
            return round(self.entry_price - dist, 4)
        else:
            return round(self.entry_price + dist, 4)

    # ── Profit in ATR units ──────────────────────
    def _profit_atr(self, price: float) -> float:
        if self.direction == "LONG":
            return (price - self.entry_price) / self.atr
        else:
            return (self.entry_price - price) / self.atr

    # ── Trail distance from price ────────────────
    def _trail_stop_from(self, price: float) -> float:
        dist = self.cfg.atr_trail_mult * self.atr
        if self.direction == "LONG":
            return round(price - dist, 4)
        else:
            return round(price + dist, 4)

    # ── Core update — call on every bar / tick ───
    def update(self, current_price: float) -> str:
        """
        Feed the latest price and get back an action string.

        Returns
        -------
        "HOLD"       — no change, trade continues
        "MOVE_STOP"  — stop was moved (check self.current_stop for new level)
        "BREAKEVEN"  — stop moved to entry price
        "STOP_HIT"   — price crossed stop → close the trade
        """
        if self.is_closed:
            return "CLOSED"

        profit_atr = self._profit_atr(current_price)

        # ── 1. Check if stop is hit ──────────────
        if self.direction == "LONG" and current_price <= self.current_stop:
            return self._close("STOP_HIT")
        if self.direction == "SHORT" and current_price >= self.current_stop:
            return self._close("STOP_HIT")

        # ── 2. Breakeven lock ────────────────────
        if (
            self.cfg.enable_breakeven
            and not self.breakeven_set
            and profit_atr >= self.cfg.breakeven_mult
        ):
            be_stop = self.entry_price
            if self._stop_is_better(be_stop):
                self.current_stop  = be_stop
                self.breakeven_set = True
                self.stop_history.append(
                    {"event": "BREAKEVEN", "stop": be_stop, "price": current_price}
                )
                return "BREAKEVEN"

        # ── 3. Activate trailing once profit ≥ activation_mult × ATR ──
        if not self.trailing_active and profit_atr >= self.cfg.activation_mult:
            self.trailing_active = True

        # ── 4. Trail the stop ────────────────────
        if self.trailing_active:
            # Track the extreme price
            if self.direction == "LONG":
                self.highest_price = max(self.highest_price, current_price)
                new_stop = self._trail_stop_from(self.highest_price)
            else:
                self.lowest_price = min(self.lowest_price, current_price)
                new_stop = self._trail_stop_from(self.lowest_price)

            if self._stop_is_better(new_stop):
                self.current_stop = new_stop
                self.stop_history.append(
                    {"event": "TRAIL", "stop": new_stop, "price": current_price}
                )
                return "MOVE_STOP"

        return "HOLD"

    # ── Helper: is new stop better than current? ─
    def _stop_is_better(self, new_stop: float) -> bool:
        if self.direction == "LONG":
            return new_stop > self.current_stop
        else:
            return new_stop < self.current_stop

    # ── Close the trade ──────────────────────────
    def _close(self, reason: str) -> str:
        self.is_closed    = True
        self.close_reason = reason
        self.stop_history.append(
            {"event": reason, "stop": self.current_stop, "price": self.current_stop}
        )
        return reason

    # ── Snapshot ─────────────────────────────────
    def status(self) -> dict:
        return {
            "direction"       : self.direction,
            "entry_price"     : self.entry_price,
            "current_stop"    : self.current_stop,
            "initial_stop"    : self.initial_stop,
            "trailing_active" : self.trailing_active,
            "breakeven_set"   : self.breakeven_set,
            "is_closed"       : self.is_closed,
            "close_reason"    : self.close_reason,
            "stop_moves"      : len([h for h in self.stop_history if h["event"] == "TRAIL"]),
        }


# ─────────────────────────────────────────────
#  Smoke test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Trailing Stop — LONG trade simulation ===\n")

    ts = TrailingStop(direction="LONG", entry_price=4561.00, atr=8.50)
    print(f"Initial stop : {ts.initial_stop}")

    price_path = [
        4561, 4563, 4558, 4565, 4570,   # chop around entry
        4572, 4575, 4578,                # profit builds → breakeven triggers
        4582, 4588, 4591,                # trail activates
        4595, 4598, 4601,                # stop trails up
        4595, 4589, 4581,                # price pulls back → stop hit
    ]

    for price in price_path:
        action = ts.update(price)
        print(f"  price={price:<8}  stop={ts.current_stop:<10}  action={action}")
        if action == "STOP_HIT":
            break

    print(f"\nFinal status: {ts.status()}")
