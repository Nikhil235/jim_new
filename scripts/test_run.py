"""
$1,000 Investment Simulation with Mini-Medallion (Zero Commission)
==================================================================
Demonstrates how the AI models generate returns with a small $1,000 account
by removing broker commissions to isolate pure model performance.

Run with:  d:\\AI\\Jim\\.venv\\Scripts\\python.exe scripts\\test_run.py
"""

import requests
import time
import sys
import os
import pandas as pd

BASE_URL = "http://localhost:8000"

def simulate_1000_dollars():
    print("=" * 60)
    print("  $1,000 INVESTMENT SIMULATION (STATISTICAL RUN)")
    print("=" * 60)

    # 0. Stop any existing engine first
    try:
        requests.post(f"{BASE_URL}/paper-trading/stop")
        time.sleep(1)
    except Exception:
        pass

    # 1. Start Paper Trading with $1,000
    print("\n[STEP 1] Starting engine with $1,000 (zero fees)...")
    try:
        start_resp = requests.post(
            f"{BASE_URL}/paper-trading/start",
            json={
                "initial_capital": 1000.0,
                "kelly_fraction": 0.25,
                "max_position_pct": 0.10,
                "max_daily_loss_pct": 0.05,
                "min_confidence": 0.65,
                "commission_per_trade": 0.0,
                "slippage_pct": 0.0,
            },
        )
        data = start_resp.json()
        print(f"   OK: {data.get('message', 'Started')}")
    except requests.exceptions.ConnectionError:
        print("   ERROR: Backend not running on port 8000!")
        return

    time.sleep(0.5)

    # 2. Fetch Large Dataset (60 Days / 15-Min)
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from src.paper_trading.live_inference import (
        run_wavelet, run_hmm, run_lstm, run_tft, run_genetic, run_ensemble, fetch_live_gold_data, run_nlp_sentiment
    )
    from src.paper_trading.prediction_logger import log_prediction_cycle

    print("\n[STEP 2] Fetching 60 Days of 15m historical data...")
    df_full = fetch_live_gold_data(period="60d", interval="15m")
    
    if df_full is None or len(df_full) < 1500:
        print(f"Not enough data fetched. Only got {len(df_full) if df_full is not None else 0} bars.")
        return

    # Simulate 1,000 continuous bars
    sim_length = 1000
    start_idx = len(df_full) - sim_length

    wins = 0
    losses = 0
    trades_taken = 0

    # Fetch NLP sentiment ONCE for the simulation to avoid 5000+ network requests
    print("\n[STEP 3] Fetching initial NLP Sentiment...")
    try:
        nlp_res = run_nlp_sentiment()
        print(f"   NLP Sentiment: {nlp_res['signal']} (Conf: {nlp_res['confidence']:.2f})")
    except Exception as e:
        print(f"   Failed to fetch NLP, defaulting to HOLD: {e}")
        nlp_res = {"signal": "HOLD", "confidence": 0.0, "reasoning": "Failed to fetch"}

    print(f"\n[STEP 4] Running Simulation for {sim_length} bars...")
    print("=" * 60)

    for step in range(sim_length):
        current_idx = start_idx + step
        df_slice: pd.DataFrame = df_full.iloc[:current_idx+1].copy()  # type: ignore
        current_price = float(df_slice["close"].iloc[-1])
        
        # Progress indicator every 100 bars
        if (step + 1) % 100 == 0:
            print(f"   [Progress] Processed {step + 1}/{sim_length} bars...")

        # Run models silently (NLP is reused to prevent network spam)
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
            "wavelet": wavelet_res, "hmm": hmm_res, "lstm": lstm_res,
            "tft": tft_res, "genetic": genetic_res, "nlp": nlp_res,
        }
        
        ensemble_res = run_ensemble(individual, regime, macro_data)
        
        direction = ensemble_res["signal"]
        conf = ensemble_res["confidence"]
        reason = ensemble_res["reasoning"]
        trade_taken = direction in ["LONG", "SHORT"] and float(conf) >= 0.65
        
        log_prediction_cycle(
            price=current_price, regime=regime,
            all_signals={**individual, "ensemble": ensemble_res},
            kelly_fraction=0.25, trade_taken=trade_taken,
        )
        
        if not trade_taken:
            continue
            
        # Post the signal to engine
        resp = requests.post(
            f"{BASE_URL}/paper-trading/signal",
            json={
                "model_name": "ensemble", "signal_type": direction,
                "confidence": float(conf), "price": current_price,
                "regime": regime, "reasoning": reason,
            },
        )
        
        result = resp.json()
        executed = result.get("trade_executed", False)
        
        if executed:
            trades_taken += 1
            trade_info = result.get("trade", {})
            qty = trade_info.get("quantity", 0)
            print(f"   [TRADE] Opened {direction} {qty:.4f} oz @ ${current_price:,.2f} (Conf: {conf:.3f})")
            
            # Simulate 1 step lookahead for exit
            if current_idx + 1 < len(df_full):
                next_price = float(df_full["close"].iloc[current_idx + 1])
            else:
                next_price = current_price
                
            requests.post(
                f"{BASE_URL}/paper-trading/signal",
                json={
                    "model_name": "ensemble", "signal_type": "CLOSE",
                    "confidence": 0.90, "price": next_price,
                    "regime": regime, "reasoning": "Simulated Exit",
                },
            )
            
            expected = "UP" if (direction == "LONG" and next_price > current_price) or (direction == "SHORT" and next_price < current_price) else "DOWN"
            if expected == "UP":
                wins += 1
                print(f"           ↳ WIN  | Exited @ ${next_price:,.2f}")
            else:
                losses += 1
                print(f"           ↳ LOSS | Exited @ ${next_price:,.2f}")

    # 4. Final Summary
    print(f"\n{'==='*20}")
    print("  FINAL SIMULATION RESULTS")
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
    if trades_taken > 0:
        print(f"  Win Rate:          {win_rate * 100:.1f}% ({wins}W / {losses}L)")
    else:
        print(f"  Win Rate:          0.0% (0W / 0L)")
    print(f"  Sharpe Ratio:      {sharpe:.2f}")
    print(f"  Max Drawdown:      {max_dd:.2f}%")
    print(f"  Total Trades:      {num_trades}")

    trades_resp = requests.get(f"{BASE_URL}/paper-trading/trades?limit=50").json()
    if trades_resp:
        print(f"\n  {'- '*28}")
        print(f"  {'#':<4} {'Type':<6} {'Entry':>9} {'Exit':>9} {'P&L':>10} {'Result'}")
        print(f"  {'- '*28}")
        for idx, t in enumerate(trades_resp[:15], 1):  # Show top 15 max
            exit_p = f"${t['exit_price']:,.2f}" if t["exit_price"] else "  OPEN"
            pnl_val = t["pnl"]
            tag = "WIN" if pnl_val > 0 else "LOSS"
            print(f"  {idx:<4} {t['signal_type']:<6} ${t['entry_price']:>7,.2f} {exit_p:>9} ${pnl_val:>9,.2f}  {tag}")
        if len(trades_resp) > 15:
            print(f"  ... and {len(trades_resp) - 15} more trades.")

    print("\n  NOTE: This is PAPER TRADING - no real money was used.")
    print(f"{'==='*20}\n")

if __name__ == "__main__":
    simulate_1000_dollars()
