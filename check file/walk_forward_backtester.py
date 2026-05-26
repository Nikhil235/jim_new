"""
walk_forward_backtester.py
==========================
Walk-forward backtester for Gold/Silver strategies.
Slots directly into your existing best_hybrid_run.py pipeline.

Quick start:
    from walk_forward_backtester import WalkForwardBacktester, BacktestConfig

    config = BacktestConfig(
        train_days   = 40,
        test_days    = 10,
        risk_pct     = 0.01,     # 1 % of capital per trade
        rr_ratio     = 2.0,      # 1:2 risk-reward
        slippage     = 0.30,     # $0.30 per oz (realistic for gold)
        spread       = 0.35,     # normal spread
        leverage     = 10,
        capital      = 10_000,
    )

    wf  = WalkForwardBacktester(df, signal_fn, config)
    rep = wf.run()
    wf.print_report(rep)
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Callable, List, Dict, Any
from adx_regime_detector import RegimeDetector, trend_filter, compute_ema, compute_atr


# ─────────────────────────────────────────────
#  Configuration dataclass
# ─────────────────────────────────────────────

@dataclass
class BacktestConfig:
    # Walk-forward window sizes (in calendar days)
    train_days   : int   = 40
    test_days    : int   = 10

    # Trade sizing
    capital      : float = 10_000.0
    risk_pct     : float = 0.01       # fraction of capital risked per trade
    rr_ratio     : float = 2.0        # reward-to-risk multiple
    leverage     : int   = 10

    # Realistic execution costs
    slippage     : float = 0.30       # $/oz added to fill (each side)
    spread       : float = 0.35       # $/oz spread cost (normal)
    news_spread  : float = 2.50       # $/oz spread during news windows

    # News window hours (UTC) — spreads widen around these
    news_hours   : List[int] = field(default_factory=lambda: [13, 14, 18, 19])

    # Confidence threshold passed to your AI signal function
    confidence_threshold: float = 0.55


# ─────────────────────────────────────────────
#  Single trade result
# ─────────────────────────────────────────────

@dataclass
class Trade:
    entry_time  : Any
    exit_time   : Any
    direction   : str        # "LONG" | "SHORT"
    entry_price : float
    exit_price  : float
    stop_price  : float
    target_price: float
    outcome     : str        # "TP" | "SL" | "OPEN"
    pnl_usd     : float
    regime      : str
    window_id   : int


# ─────────────────────────────────────────────
#  Walk-Forward Backtester
# ─────────────────────────────────────────────

class WalkForwardBacktester:
    """
    Splits historical OHLCV data into rolling train/test windows and
    runs your signal function only on out-of-sample (test) bars.

    Parameters
    ----------
    df        : Full OHLCV DataFrame with a DatetimeIndex
    signal_fn : Callable[[pd.DataFrame], tuple[str, float]]
                    Receives the training window + all bars up to current bar.
                    Returns (direction, confidence) e.g. ("LONG", 0.72)
                    Return ("NONE", 0.0) if no signal.
    config    : BacktestConfig instance
    """

    def __init__(
        self,
        df        : pd.DataFrame,
        signal_fn : Callable[[pd.DataFrame], tuple],
        config    : BacktestConfig,
    ):
        self.df        = df.copy().sort_index()
        self.signal_fn = signal_fn
        self.cfg       = config
        self._prepare_df()

    # ── Data preparation ─────────────────────────
    def _prepare_df(self):
        df = self.df
        df["ema50"]  = compute_ema(df["close"], 50)
        df["ema200"] = compute_ema(df["close"], 200)
        df["atr"]    = compute_atr(df, 14)
        self.df = df

    def _spread(self, ts) -> float:
        """Return news or normal spread based on the bar's hour (UTC)."""
        try:
            hour = pd.Timestamp(ts).hour
        except Exception:
            return self.cfg.spread
        return self.cfg.news_spread if hour in self.cfg.news_hours else self.cfg.spread

    # ── Position sizing ──────────────────────────
    def _calc_stop_and_target(
        self,
        direction  : str,
        entry_price: float,
        atr_value  : float,
    ) -> tuple[float, float]:
        """Stop = 1.5×ATR away; Target = stop × RR ratio."""
        stop_dist   = 1.5 * atr_value
        target_dist = stop_dist * self.cfg.rr_ratio

        if direction == "LONG":
            stop   = entry_price - stop_dist
            target = entry_price + target_dist
        else:
            stop   = entry_price + stop_dist
            target = entry_price - target_dist

        return round(stop, 4), round(target, 4)

    def _calc_lot_size(
        self,
        entry_price : float,
        stop_price  : float,
        capital     : float,
        pos_mult    : float,
    ) -> float:
        """Risk-based lot sizing scaled by regime position multiplier."""
        risk_dollars  = capital * self.cfg.risk_pct * pos_mult
        stop_distance = abs(entry_price - stop_price)
        if stop_distance == 0:
            return 0.0
        # lot size in troy oz
        lot_oz = (risk_dollars * self.cfg.leverage) / stop_distance
        return max(round(lot_oz, 4), 0.0)

    # ── Core walk-forward loop ───────────────────
    def run(self) -> Dict:
        """
        Execute walk-forward test.
        Returns a results dict with per-window stats and full trade list.
        """
        df      = self.df
        cfg     = self.cfg
        trades  : List[Trade] = []
        windows : List[Dict]  = []

        # Build date-based windows
        start_date = df.index[0]
        end_date   = df.index[-1]
        wid        = 0

        cursor = start_date
        while True:
            train_end = cursor + pd.Timedelta(days=cfg.train_days)
            test_end  = train_end + pd.Timedelta(days=cfg.test_days)

            if test_end > end_date:
                break

            train_df = df[cursor    : train_end]
            test_df  = df[train_end : test_end]

            if len(train_df) < 200 or len(test_df) == 0:
                cursor = train_end
                wid   += 1
                continue

            window_trades = self._run_window(train_df, test_df, wid)
            trades.extend(window_trades)

            win_pnl  = sum(t.pnl_usd for t in window_trades)
            win_wins = sum(1 for t in window_trades if t.outcome == "TP")
            windows.append({
                "window"     : wid,
                "train_start": cursor,
                "train_end"  : train_end,
                "test_start" : train_end,
                "test_end"   : test_end,
                "trades"     : len(window_trades),
                "wins"       : win_wins,
                "pnl_usd"    : round(win_pnl, 2),
            })

            cursor = train_end   # slide window forward
            wid   += 1

        return self._compile_report(trades, windows)

    # ── Single window execution ──────────────────
    def _run_window(
        self,
        train_df : pd.DataFrame,
        test_df  : pd.DataFrame,
        wid      : int,
    ) -> List[Trade]:
        """Simulate bar-by-bar on the out-of-sample test window."""
        cfg      = self.cfg
        trades   : List[Trade] = []
        capital  = cfg.capital   # capital resets per window (change if you want cumulative)
        open_trade: dict | None = None

        # Combine train + test for indicator computation
        full_context = pd.concat([train_df, test_df])

        for i, (ts, row) in enumerate(test_df.iterrows()):
            # Bars available up to and including this one (no look-ahead)
            bars_so_far = full_context.loc[:ts]

            # ── 1. Check if open trade hits TP or SL ──
            if open_trade:
                hi = row["high"]
                lo = row["low"]
                ot = open_trade

                if ot["direction"] == "LONG":
                    if lo <= ot["stop"]:
                        trades.append(self._close_trade(ot, ot["stop"], ts, "SL", wid))
                        open_trade = None
                    elif hi >= ot["target"]:
                        trades.append(self._close_trade(ot, ot["target"], ts, "TP", wid))
                        open_trade = None
                else:  # SHORT
                    if hi >= ot["stop"]:
                        trades.append(self._close_trade(ot, ot["stop"], ts, "SL", wid))
                        open_trade = None
                    elif lo <= ot["target"]:
                        trades.append(self._close_trade(ot, ot["target"], ts, "TP", wid))
                        open_trade = None

            # ── 2. Skip if already in a trade ─────────
            if open_trade:
                continue

            # ── 3. Get AI signal ───────────────────────
            if len(bars_so_far) < 210:
                continue

            try:
                direction, confidence = self.signal_fn(bars_so_far)
            except Exception:
                continue

            if direction == "NONE" or confidence < cfg.confidence_threshold:
                continue

            # ── 4. Apply regime filter ─────────────────
            detector = RegimeDetector(bars_so_far)
            regime   = detector.detect()
            pos_mult = detector.position_multiplier()

            allowed  = trend_filter(bars_so_far, confidence, cfg.confidence_threshold)
            if not allowed:
                continue

            # ── 5. Size and enter ──────────────────────
            spread      = self._spread(ts)
            slippage    = cfg.slippage
            entry_price = row["close"] + slippage + (spread / 2)  # realistic fill

            atr_val = float(bars_so_far["atr"].iloc[-1])
            stop, target = self._calc_stop_and_target(direction, entry_price, atr_val)

            lot_oz = self._calc_lot_size(entry_price, stop, capital, pos_mult)
            if lot_oz <= 0:
                continue

            open_trade = {
                "entry_time" : ts,
                "direction"  : direction,
                "entry_price": entry_price,
                "stop"       : stop,
                "target"     : target,
                "lot_oz"     : lot_oz,
                "regime"     : regime,
                "spread_cost": spread * lot_oz,
            }

        # Close any trade still open at window end
        if open_trade:
            last_price = test_df.iloc[-1]["close"]
            trades.append(
                self._close_trade(open_trade, last_price, test_df.index[-1], "OPEN", wid)
            )

        return trades

    # ── Trade closing helper ─────────────────────
    def _close_trade(
        self,
        ot        : dict,
        exit_price: float,
        exit_time : Any,
        outcome   : str,
        wid       : int,
    ) -> Trade:
        direction = ot["direction"]
        lot_oz    = ot["lot_oz"]
        raw_pnl   = (exit_price - ot["entry_price"]) * lot_oz
        if direction == "SHORT":
            raw_pnl = -raw_pnl

        # Deduct spread cost on entry and exit
        net_pnl = raw_pnl - ot.get("spread_cost", 0) - (self.cfg.spread * lot_oz)

        return Trade(
            entry_time  = ot["entry_time"],
            exit_time   = exit_time,
            direction   = direction,
            entry_price = ot["entry_price"],
            exit_price  = round(exit_price, 4),
            stop_price  = ot["stop"],
            target_price= ot["target"],
            outcome     = outcome,
            pnl_usd     = round(net_pnl, 2),
            regime      = ot["regime"],
            window_id   = wid,
        )

    # ── Report compilation ───────────────────────
    def _compile_report(self, trades: List[Trade], windows: List[Dict]) -> Dict:
        if not trades:
            return {
                "summary" : {
                    "total_trades": 0,
                    "windows_tested": len(windows),
                    "message": "No trades generated — check signal_fn or confidence threshold.",
                },
                "trades"  : [],
                "windows" : windows,
            }

        closed = [t for t in trades if t.outcome in ("TP", "SL")]
        wins   = [t for t in closed if t.outcome == "TP"]
        losses = [t for t in closed if t.outcome == "SL"]

        total_pnl  = sum(t.pnl_usd for t in trades)
        win_rate   = len(wins) / len(closed) * 100 if closed else 0
        avg_win    = np.mean([t.pnl_usd for t in wins])   if wins   else 0
        avg_loss   = np.mean([t.pnl_usd for t in losses]) if losses else 0
        profit_factor = (
            abs(sum(t.pnl_usd for t in wins)) /
            abs(sum(t.pnl_usd for t in losses))
            if losses else float("inf")
        )

        # Max drawdown
        equity = np.cumsum([t.pnl_usd for t in trades])
        peak   = np.maximum.accumulate(equity)
        dd     = equity - peak
        max_dd = float(dd.min())

        # By regime
        regime_stats: Dict[str, Dict] = {}
        for t in closed:
            r = t.regime
            if r not in regime_stats:
                regime_stats[r] = {"trades": 0, "wins": 0, "pnl": 0.0}
            regime_stats[r]["trades"] += 1
            regime_stats[r]["wins"]   += (1 if t.outcome == "TP" else 0)
            regime_stats[r]["pnl"]    += t.pnl_usd

        return {
            "summary": {
                "total_trades"     : len(trades),
                "closed_trades"    : len(closed),
                "wins"             : len(wins),
                "losses"           : len(losses),
                "win_rate_pct"     : round(win_rate, 1),
                "total_pnl_usd"    : round(total_pnl, 2),
                "avg_win_usd"      : round(avg_win,  2),
                "avg_loss_usd"     : round(avg_loss, 2),
                "profit_factor"    : round(profit_factor, 2),
                "max_drawdown_usd" : round(max_dd, 2),
                "windows_tested"   : len(windows),
            },
            "by_regime" : regime_stats,
            "windows"   : windows,
            "trades"    : [t.__dict__ for t in trades],
        }

    @staticmethod
    def print_report(report: Dict):
        """Pretty-print the backtest summary to the terminal."""
        s = report["summary"]
        print("\n" + "═" * 50)
        print("  WALK-FORWARD BACKTEST RESULTS")
        print("═" * 50)
        print(f"  Windows tested    : {s['windows_tested']}")
        print(f"  Total trades      : {s['total_trades']}")
        print(f"  Win rate          : {s['win_rate_pct']}%")
        print(f"  Total P&L         : ${s['total_pnl_usd']:,.2f}")
        print(f"  Avg win           : ${s['avg_win_usd']:,.2f}")
        print(f"  Avg loss          : ${s['avg_loss_usd']:,.2f}")
        print(f"  Profit factor     : {s['profit_factor']}")
        print(f"  Max drawdown      : ${s['max_drawdown_usd']:,.2f}")

        if report.get("by_regime"):
            print("\n  ── P&L by Regime ──")
            for regime, rs in report["by_regime"].items():
                wr = round(rs["wins"] / rs["trades"] * 100, 1) if rs["trades"] else 0
                print(f"  {regime:<12} trades={rs['trades']}  win={wr}%  pnl=${rs['pnl']:,.2f}")

        if report.get("windows"):
            print("\n  ── Per Window ──")
            for w in report["windows"]:
                print(
                    f"  Window {w['window']:02d}  "
                    f"{str(w['test_start'])[:10]} → {str(w['test_end'])[:10]}  "
                    f"trades={w['trades']}  wins={w['wins']}  pnl=${w['pnl_usd']:,.2f}"
                )
        print("═" * 50 + "\n")


# ─────────────────────────────────────────────
#  Demo — runs with a stub signal function
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import random

    # ── Synthetic gold-like price data ──
    np.random.seed(0)
    n      = 2000
    dates  = pd.date_range("2024-11-01", periods=n, freq="15min")
    close  = 4400 + np.cumsum(np.random.randn(n) * 6)
    df_demo = pd.DataFrame({
        "open"  : close - np.abs(np.random.randn(n) * 2),
        "high"  : close + np.abs(np.random.randn(n) * 5),
        "low"   : close - np.abs(np.random.randn(n) * 5),
        "close" : close,
        "volume": np.random.randint(200, 800, n),
    }, index=dates)

    # ── Stub signal function — replace with your AI model ──
    def my_signal(bars: pd.DataFrame):
        """
        Replace this with your real AI model call.
        Must return (direction: str, confidence: float)
        """
        confidence = random.uniform(0.45, 0.80)
        direction  = random.choice(["LONG", "SHORT", "NONE"])
        return direction, confidence

    # ── Run the backtester ──
    cfg = BacktestConfig(
        train_days = 30,
        test_days  = 10,
        capital    = 10_000,
        risk_pct   = 0.01,
        rr_ratio   = 2.0,
        leverage   = 10,
        slippage   = 0.30,
        spread     = 0.35,
    )

    wf     = WalkForwardBacktester(df_demo, my_signal, cfg)
    report = wf.run()
    WalkForwardBacktester.print_report(report)
