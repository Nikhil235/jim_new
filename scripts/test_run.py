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
    # Simulate 100 realistic trades across actual models
    # ---------------------------------------------------------------
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    
    import pandas as pd
    from src.paper_trading.live_inference import (
        run_wavelet, run_hmm, run_lstm, run_tft, run_genetic, run_ensemble, fetch_live_gold_data
    )
    from src.paper_trading.prediction_logger import log_prediction_cycle

    print("\n[STEP 2] Fetching historical data for simulation...")
    df_full = fetch_live_gold_data(period="1mo", interval="1h")
    
    if df_full is None or len(df_full) < 130:
        print("Not enough data fetched.")
        return

    # We will simulate the last 100 bars
    sim_length = 100
    start_idx = len(df_full) - sim_length

    wins = 0
    losses = 0

    for step in range(sim_length):
        current_idx = start_idx + step
        # Type hint to resolve static checker confusion: iloc slice returns a DataFrame
        df_slice: pd.DataFrame = df_full.iloc[:current_idx+1].copy()  # type: ignore
        current_price = float(df_slice["close"].iloc[-1])
        
        print(f"\n{'---'*20}")
        print(f"[TRADE {step+1}/{sim_length}] Analyzing price: ${current_price:,.2f}")
        
        # ACTUALLY run the real models
        wavelet_res = run_wavelet(df_slice)
        hmm_res = run_hmm(df_slice)
        lstm_res = run_lstm(df_slice)
        tft_res = run_tft(df_slice)
        genetic_res = run_genetic(df_slice)
        
        regime = hmm_res.get("regime", "NORMAL")
        macro_data = {
            "dxy_momentum": float(df_slice["dxy_returns"].iloc[-3:].sum() * 100) if "dxy_returns" in df_slice.columns else 0.0,
            "yield_momentum": float(df_slice["us10y_returns"].iloc[-3:].sum() * 100) if "us10y_returns" in df_slice.columns else 0.0,
        }
        
        individual = {
            "wavelet": wavelet_res,
            "hmm": hmm_res,
            "lstm": lstm_res,
            "tft": tft_res,
            "genetic": genetic_res,
        }
        
        # Run ensemble meta-learner
        ensemble_res = run_ensemble(individual, regime, macro_data)
        
        model_outputs = {
            **individual,
            "ensemble": ensemble_res
        }
        
        # Print actual model outputs
        print(f"   Wavelet : {wavelet_res['signal']:5} (conf: {wavelet_res['confidence']:.2f})")
        print(f"   HMM     : {hmm_res['signal']:5} (conf: {hmm_res['confidence']:.2f})")
        print(f"   LSTM    : {lstm_res['signal']:5} (conf: {lstm_res['confidence']:.2f})")
        print(f"   TFT     : {tft_res['signal']:5} (conf: {tft_res['confidence']:.2f})")
        print(f"   Genetic : {genetic_res['signal']:5} (conf: {genetic_res['confidence']:.2f})")
        print(f"   => ENSEMBLE: {ensemble_res['signal']} (conf: {ensemble_res['confidence']:.2f})")
        
        # We simulate the entry
        direction = ensemble_res["signal"]
        conf = ensemble_res["confidence"]
        reason = ensemble_res["reasoning"]
        
        trade_taken = direction in ["LONG", "SHORT"] and float(conf) >= 0.60
        
        if not trade_taken:
            print("   Action: HOLD (Confidence too low or NO signal)")
            continue
            
        # Post the ensemble signal
        resp = requests.post(
            f"{BASE_URL}/paper-trading/signal",
            json={
                "model_name": "ensemble",
                "signal_type": direction,
                "confidence": float(conf),
                "price": current_price,
                "regime": regime,
                "reasoning": reason,
            },
        )
        
        result = resp.json()
        executed = result.get("trade_executed", False)
        
        if executed:
            trade_info = result.get("trade", {})
            qty = trade_info.get("quantity", 0)
            value = qty * current_price
            print(f"   Opened: {direction} {qty:.4f} oz (${value:,.2f})")
        else:
            print(f"   Signal skipped by engine limits.")
            continue
            
        time.sleep(0.1)
        
        # Look ahead 1 step to simulate price move and exit
        if current_idx + 1 < len(df_full):
            next_price = float(df_full["close"].iloc[current_idx + 1])
        else:
            next_price = current_price
            
        # Close position
        close_resp = requests.post(
            f"{BASE_URL}/paper-trading/signal",
            json={
                "model_name": "ensemble",
                "signal_type": "CLOSE",
                "confidence": 0.90,
                "price": next_price,
                "regime": regime,
                "reasoning": "Target/stop reached on next bar.",
            },
        )
        time.sleep(0.1)
        
        # Get updated P&L
        perf = requests.get(f"{BASE_URL}/paper-trading/performance").json()
        total_val = perf.get("total_value", 0)
        pnl = perf.get("pnl_total", 0)
        move = next_price - current_price
        
        expected = "UP" if (direction == "LONG" and next_price > current_price) or (direction == "SHORT" and next_price < current_price) else "DOWN"
        will_win = expected == "UP"
        
        if will_win:
            wins += 1
            print(f"   >> WIN  | Price moved to ${next_price:,.2f}")
        else:
            losses += 1
            print(f"   >> LOSS | Price moved to ${next_price:,.2f}")
            
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
