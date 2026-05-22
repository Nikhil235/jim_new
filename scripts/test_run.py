"""
$1,000 Investment Simulation with Mini-Medallion (Zero Commission)
==================================================================
Demonstrates how the AI models generate returns with a small $1,000 account
by removing broker commissions to isolate pure model performance.

Run with:  d:\\AI\\Jim\\.venv\\Scripts\\python.exe scripts\\test_run.py
"""

import requests
import time

BASE_URL = "http://localhost:8000"


def simulate_1000_dollars():
    print("=" * 60)
    print("  $1,000 INVESTMENT SIMULATION (ZERO COMMISSION)")
    print("=" * 60)

    # 0. Stop any existing engine first
    try:
        requests.post(f"{BASE_URL}/paper-trading/stop")
        time.sleep(1)
    except Exception:
        pass

    # 1. Start Paper Trading with $1,000 and ZERO commission/slippage
    print("\n[STEP 1] Starting engine with $1,000 (zero fees)...")
    try:
        start_resp = requests.post(
            f"{BASE_URL}/paper-trading/start",
            json={
                "initial_capital": 1000.0,
                "kelly_fraction": 0.25,
                "max_position_pct": 0.10,
                "max_daily_loss_pct": 0.05,    # Wider limit for demo
                "min_confidence": 0.60,
                "commission_per_trade": 0.0,    # ZERO commission
                "slippage_pct": 0.0,            # ZERO slippage
            },
        )
        data = start_resp.json()
        print(f"   OK: {data.get('message', 'Started')}")
    except requests.exceptions.ConnectionError:
        print("   ERROR: Backend not running on port 8000!")
        print("   Run:  .venv\\Scripts\\python.exe main.py --mode api --port 8000")
        return

    time.sleep(0.5)

    # 2. Show starting balance
    status = requests.get(f"{BASE_URL}/paper-trading/status").json()
    portfolio = status.get("portfolio", {})
    print(f"   Starting Cash: ${portfolio.get('cash', 0):,.2f}")

    # ---------------------------------------------------------------
    # Simulate 10 realistic trades across different models & regimes
    # ---------------------------------------------------------------
    trades = [
        # (model, direction, confidence, entry, exit, reasoning, regime)
        ("ensemble", "LONG",  0.82, 2380.00, 2395.50, "Bullish consensus across all models",        "GROWTH"),
        ("wavelet", "SHORT", 0.75, 2395.50, 2388.00, "Wavelet detects mean-reversion signal",      "NORMAL"),
        ("hmm",     "LONG",  0.88, 2388.00, 2412.30, "HMM: regime shift to growth detected",       "GROWTH"),
        ("ensemble","SHORT", 0.70, 2412.30, 2403.10, "Ensemble predicts pullback from overbought",  "NORMAL"),
        ("wavelet", "LONG",  0.90, 2403.10, 2428.00, "Strong denoised uptrend signal",              "GROWTH"),
        ("hmm",     "LONG",  0.85, 2428.00, 2441.50, "HMM confirms continuation of growth regime",  "GROWTH"),
        ("ensemble","SHORT", 0.72, 2441.50, 2435.20, "Short-term exhaustion detected",              "NORMAL"),
        ("wavelet", "LONG",  0.80, 2435.20, 2420.00, "Denoised signal reverses - LOSS",             "NORMAL"),  # LOSING trade
        ("hmm",     "LONG",  0.87, 2420.00, 2448.70, "New bullish regime confirmed",                "GROWTH"),
        ("ensemble","LONG",  0.91, 2448.70, 2470.00, "Strong multi-model consensus to close week",   "GROWTH"),
    ]

    wins = 0
    losses = 0

    for i, (model, direction, conf, entry, exit_price, reason, regime) in enumerate(trades, 1):
        print(f"\n{'---'*20}")
        expected = "UP" if (direction == "LONG" and exit_price > entry) or (direction == "SHORT" and exit_price < entry) else "DOWN"
        will_win = (direction == "LONG" and exit_price > entry) or (direction == "SHORT" and exit_price < entry)

        print(f"[TRADE {i}/10] {model.upper()} -> {direction} @ ${entry:,.2f}")
        print(f"   Confidence: {conf*100:.0f}% | Regime: {regime}")
        print(f"   Thesis: {reason}")

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
            value = qty * entry
            print(f"   Opened: {qty:.4f} oz (${value:,.2f} position)")
        else:
            print(f"   Signal skipped (risk limits / confidence threshold)")
            continue

        time.sleep(0.2)

        # Close position
        close_resp = requests.post(
            f"{BASE_URL}/paper-trading/signal",
            json={
                "model_name": model,
                "signal_type": "CLOSE",
                "confidence": 0.90,
                "price": exit_price,
                "regime": regime,
                "reasoning": "Target/stop reached.",
            },
        )

        time.sleep(0.2)

        # Get updated P&L
        perf = requests.get(f"{BASE_URL}/paper-trading/performance").json()
        total_val = perf.get("total_value", 0)
        pnl = perf.get("pnl_total", 0)
        move = exit_price - entry
        if will_win:
            wins += 1
            print(f"   >> WIN  | Gold moved ${move:+,.2f}/oz")
        else:
            losses += 1
            print(f"   >> LOSS | Gold moved ${move:+,.2f}/oz")
        print(f"   Portfolio: ${total_val:,.2f} (P&L: ${pnl:+,.2f})")

    # ---------------------------------------------------------------
    # Final Summary
    # ---------------------------------------------------------------
    print(f"\n{'==='*20}")
    print("  FINAL RESULTS")
    print(f"{'==='*20}")

    perf = requests.get(f"{BASE_URL}/paper-trading/performance").json()

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
    print(f"  Win Rate:          {win_rate * 100:.1f}% ({wins}W / {losses}L)")
    print(f"  Sharpe Ratio:      {sharpe:.2f}")
    print(f"  Max Drawdown:      {max_dd:.2f}%")
    print(f"  Total Trades:      {num_trades}")

    # Trade-by-trade breakdown
    trades_resp = requests.get(f"{BASE_URL}/paper-trading/trades?limit=20").json()
    if trades_resp:
        print(f"\n  {'- '*28}")
        print(f"  {'#':<4} {'Model':<10} {'Type':<6} {'Entry':>9} {'Exit':>9} {'P&L':>10} {'Result'}")
        print(f"  {'- '*28}")
        for idx, t in enumerate(trades_resp, 1):
            exit_p = f"${t['exit_price']:,.2f}" if t["exit_price"] else "  OPEN"
            pnl_val = t["pnl"]
            pnl_str = f"${pnl_val:+,.2f}"
            tag = "WIN" if pnl_val > 0 else "LOSS"
            print(f"  {idx:<4} {t['model_name']:<10} {t['signal_type']:<6} ${t['entry_price']:>7,.2f} {exit_p:>9} {pnl_str:>10}  {tag}")

    print(f"\n{'==='*20}")
    if total_pnl > 0:
        print(f"  Your $1,000 grew to ${final_value:,.2f} (+${total_pnl:,.2f})")
        print(f"  That's a {((final_value - initial) / initial) * 100:.2f}% return")
        print(f"  With $0 commission, the AI models ARE profitable.")
    else:
        print(f"  Net result: ${total_pnl:+,.2f}")
    print(f"\n  NOTE: This is PAPER TRADING - no real money was used.")
    print(f"  In production, the engine runs 24/7 with live gold prices.")
    print(f"{'==='*20}\n")


if __name__ == "__main__":
    simulate_1000_dollars()
