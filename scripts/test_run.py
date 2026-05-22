"""
$1,000 Investment Simulation with Mini-Medallion
=================================================
This script demonstrates how your $1,000 grows through the
paper trading engine by simulating multiple realistic trades.

Run with:  d:\\AI\\Jim\\.venv\\Scripts\\python.exe scripts\\test_run.py
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"


def simulate_1000_dollars():
    print("=" * 60)
    print("  💰 SIMULATING $1,000 INVESTMENT IN MINI-MEDALLION")
    print("=" * 60)

    # 0. Stop any existing engine first
    try:
        requests.post(f"{BASE_URL}/paper-trading/stop")
        time.sleep(1)
    except Exception:
        pass

    # 1. Start Paper Trading with $1,000
    print("\n📌 STEP 1: Initializing Paper Trading Engine with $1,000...")
    try:
        start_resp = requests.post(
            f"{BASE_URL}/paper-trading/start",
            json={
                "initial_capital": 1000.0,
                "kelly_fraction": 0.25,       # Conservative 25% Kelly
                "max_position_pct": 0.10,     # Max 10% ($100) per trade
                "max_daily_loss_pct": 0.02,   # Stop if you lose $20/day
                "min_confidence": 0.60,
            },
        )
        data = start_resp.json()
        print(f"   ✅ {data.get('message', 'Started')}")
    except requests.exceptions.ConnectionError:
        print("   ❌ ERROR: Backend not running on port 8000!")
        print("   Run:  .venv\\Scripts\\python.exe main.py --mode api --port 8000")
        return

    time.sleep(0.5)

    # 2. Check starting portfolio
    print("\n📌 STEP 2: Starting Portfolio")
    status = requests.get(f"{BASE_URL}/paper-trading/status").json()
    portfolio = status.get("portfolio", {})
    print(f"   Cash:        ${portfolio.get('cash', 0):,.2f}")
    print(f"   Total Value: ${portfolio.get('total_value', 0):,.2f}")

    # ──────────────────────────────────────────────────────────
    # Simulate a series of realistic trades
    # ──────────────────────────────────────────────────────────
    trades = [
        # (model, direction, confidence, entry_price, exit_price, reasoning, regime)
        ("ensemble", "LONG",  0.82, 2380.00, 2395.50, "Multi-model bullish consensus",   "GROWTH"),
        ("wavelet", "SHORT", 0.75, 2395.50, 2388.00, "Wavelet detected mean-reversion",  "NORMAL"),
        ("hmm",     "LONG",  0.88, 2388.00, 2410.20, "HMM detected regime shift to growth", "GROWTH"),
        ("ensemble","SHORT", 0.70, 2410.20, 2402.80, "Overbought; ensemble predicts pullback", "NORMAL"),
        ("wavelet", "LONG",  0.90, 2402.80, 2425.00, "Strong denoised uptrend signal",   "GROWTH"),
    ]

    for i, (model, direction, conf, entry, exit_price, reason, regime) in enumerate(trades, 1):
        print(f"\n{'─' * 60}")
        print(f"📌 TRADE {i}: {model.upper()} → {direction} Gold @ ${entry:,.2f}")
        print(f"   Confidence: {conf*100:.0f}% | Regime: {regime}")
        print(f"   Reasoning: {reason}")

        # Open position
        resp = requests.post(
            f"{BASE_URL}/paper-trading/signal",
            json={
                "model_name": model,
                "signal_type": direction,
                "confidence": conf,
                "price": entry,
                "regime": regime,
                "reasoning": reason,
            },
        )
        result = resp.json()
        executed = result.get("trade_executed", False)
        if executed:
            trade_info = result.get("trade", {})
            qty = trade_info.get("quantity", 0)
            print(f"   ✅ Trade opened: {qty:.4f} oz @ ${entry:,.2f}")
        else:
            print(f"   ⚠️  Signal processed but no trade executed (risk limits / sizing)")
            continue  # Skip to next trade

        time.sleep(0.3)

        # Close position at exit price
        print(f"   📈 Gold moves to ${exit_price:,.2f} → Closing position...")
        close_resp = requests.post(
            f"{BASE_URL}/paper-trading/signal",
            json={
                "model_name": model,
                "signal_type": "CLOSE",
                "confidence": 0.90,
                "price": exit_price,
                "regime": regime,
                "reasoning": "Target reached, taking profit.",
            },
        )
        close_result = close_resp.json()

        time.sleep(0.3)

        # Check P&L after this trade
        perf = requests.get(f"{BASE_URL}/paper-trading/performance").json()
        pnl = perf.get("pnl_total", 0)
        total = perf.get("total_value", 0)
        print(f"   💵 Running P&L: ${pnl:,.2f} | Portfolio: ${total:,.2f}")

    # ──────────────────────────────────────────────────────────
    # Final Summary
    # ──────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print("  📊 FINAL RESULTS")
    print(f"{'═' * 60}")

    perf = requests.get(f"{BASE_URL}/paper-trading/performance").json()
    status = requests.get(f"{BASE_URL}/paper-trading/status").json()

    initial = 1000.0
    final_value = perf.get("total_value", initial)
    total_pnl = perf.get("pnl_total", 0)
    win_rate = perf.get("win_rate", 0)
    sharpe = perf.get("sharpe_ratio", 0)
    num_trades = perf.get("num_trades", 0)
    max_dd = perf.get("max_drawdown", 0)

    print(f"\n  Starting Capital:  ${initial:,.2f}")
    print(f"  Final Value:       ${final_value:,.2f}")
    print(f"  Total P&L:         ${total_pnl:+,.2f}")
    print(f"  Return:            {((final_value - initial) / initial) * 100:+.2f}%")
    print(f"  Win Rate:          {win_rate * 100:.1f}%")
    print(f"  Sharpe Ratio:      {sharpe:.2f}")
    print(f"  Max Drawdown:      {max_dd:.2f}%")
    print(f"  Total Trades:      {num_trades}")

    # Trade history
    trades_resp = requests.get(f"{BASE_URL}/paper-trading/trades?limit=20").json()
    if trades_resp:
        print(f"\n  {'─' * 56}")
        print(f"  {'ID':<10} {'Model':<10} {'Type':<7} {'Entry':>10} {'Exit':>10} {'P&L':>10}")
        print(f"  {'─' * 56}")
        for t in trades_resp:
            exit_p = f"${t['exit_price']:,.2f}" if t["exit_price"] else "  OPEN"
            pnl_str = f"${t['pnl']:+,.2f}"
            print(f"  {t['trade_id']:<10} {t['model_name']:<10} {t['signal_type']:<7} ${t['entry_price']:>8,.2f} {exit_p:>10} {pnl_str:>10}")

    print(f"\n{'═' * 60}")
    print("  ℹ️  This was a PAPER TRADE simulation (no real money used)")
    print("  ℹ️  In production, the engine runs 24/7 with live gold prices")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    simulate_1000_dollars()
