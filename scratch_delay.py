import time
import sys
import os
import pandas as pd
import requests

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from src.paper_trading.live_inference import (
    run_wavelet, run_hmm, run_lstm, run_tft, run_genetic, run_ensemble, fetch_live_gold_data
)
from src.paper_trading.prediction_logger import log_prediction_cycle

print("Fetching historical data...")
df_full = fetch_live_gold_data(period="60d", interval="15m")
if df_full is None or len(df_full) < 1500:
    print("Insufficient data")
    sys.exit(1)

sim_length = 5
start_idx = len(df_full) - sim_length

# Pre-train HMM
df_init = df_full.iloc[:start_idx].copy()
print("Pre-training HMM on", len(df_init), "rows...")
t0 = time.perf_counter()
run_hmm(df_init)
print(f"Pre-training HMM took: {(time.perf_counter() - t0)*1000:.3f} ms")

print("Starting 5-step simulation timing...")
for step in range(sim_length):
    print(f"\n--- STEP {step} ---")
    current_idx = start_idx + step
    df_slice = df_full.iloc[:current_idx+1].copy()
    current_price = float(df_slice["close"].iloc[-1])
    
    t_start = time.perf_counter()
    
    # NLP
    recent_ret = float(df_slice["returns"].iloc[-5:].mean())
    if recent_ret < -0.001:
        nlp_res = {"signal": "LONG", "confidence": 0.75, "reasoning": "Proxy: Risk-Off Flow"}
    elif recent_ret > 0.001:
        nlp_res = {"signal": "SHORT", "confidence": 0.75, "reasoning": "Proxy: Risk-On Flow"}
    else:
        nlp_res = {"signal": "HOLD", "confidence": 0.0, "reasoning": "Proxy: Neutral"}
    t_nlp = time.perf_counter()
    print(f"  NLP Proxy took: {(t_nlp - t_start)*1000:.3f} ms")
    
    df_slice_model = df_slice.iloc[-150:]
    
    # Wavelet
    t_sub = time.perf_counter()
    wavelet_res = run_wavelet(df_slice_model)
    t_wav = time.perf_counter()
    print(f"  Wavelet took: {(t_wav - t_sub)*1000:.3f} ms")
    
    # HMM
    hmm_res = run_hmm(df_slice_model)
    t_hmm = time.perf_counter()
    print(f"  HMM took: {(t_hmm - t_wav)*1000:.3f} ms")
    
    # LSTM
    lstm_res = run_lstm(df_slice_model)
    t_lstm = time.perf_counter()
    print(f"  LSTM took: {(t_lstm - t_hmm)*1000:.3f} ms")
    
    # TFT
    tft_res = run_tft(df_slice_model)
    t_tft = time.perf_counter()
    print(f"  TFT took: {(t_tft - t_lstm)*1000:.3f} ms")
    
    # Genetic
    genetic_res = run_genetic(df_slice_model)
    t_gen = time.perf_counter()
    print(f"  Genetic took: {(t_gen - t_tft)*1000:.3f} ms")
    
    # Macro Data & Ensemble
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
    t_ens = time.perf_counter()
    print(f"  Ensemble took: {(t_ens - t_gen)*1000:.3f} ms")
    
    # Log prediction cycle
    log_prediction_cycle(
        price=current_price, regime=regime,
        all_signals={**individual, "ensemble": ensemble_res},
        kelly_fraction=0.25, trade_taken=False,
    )
    t_log = time.perf_counter()
    print(f"  Logger took: {(t_log - t_ens)*1000:.3f} ms")
    
    print(f"  TOTAL step time: {(t_log - t_start)*1000:.3f} ms")
