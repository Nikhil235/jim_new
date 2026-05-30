#!/usr/bin/env python3
"""Run Single Live Trading Cycle - Generate Sample Logs for Dashboard"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

print("\n" + "="*100)
print("RUNNING SINGLE TRADING CYCLE - Generate Sample Data for Dashboard")
print("="*100 + "\n")

import pandas as pd
import numpy as np
from loguru import logger

# Remove debug logs
logger.remove()
logger.add(sys.stderr, level="INFO")

try:
    from src.paper_trading.live_inference import fetch_live_gold_data
    
    print("1. Fetching live gold data...")
    df = fetch_live_gold_data()
    
    if df is None or len(df) < 100:
        print("   Using synthetic data...")
        dates = pd.date_range(end="2026-05-30", periods=200, freq="1h")
        prices = 4500 + np.cumsum(np.random.randn(200) * 5)
        df = pd.DataFrame({
            "open": prices,
            "high": prices + np.abs(np.random.randn(200) * 2),
            "low": prices - np.abs(np.random.randn(200) * 2),
            "close": prices,
            "volume": np.random.randint(1000, 5000, 200),
            "dxy": 100 + np.sin(np.linspace(0, 4*np.pi, 200)) * 2,
            "us10y": 4.0 + np.cos(np.linspace(0, 4*np.pi, 200)) * 0.5,
        }, index=dates)
        df["dxy_returns"] = df["dxy"].pct_change()
        df["us10y_returns"] = df["us10y"].pct_change()
    
    print(f"   ✓ Data shape: {df.shape}")
    print(f"   ✓ Date range: {df.index[0]} to {df.index[-1]}\n")
    
    # Run all 8 models
    print("2. Running all 8 models...")
    
    from src.paper_trading.live_inference import (
        run_wavelet,
        run_wavelet_basic,
        run_hmm,
        run_lstm,
        run_tft,
        run_genetic,
        run_ensemble,
    )
    from src.models.hmm_pro_gpu import run_hmm_pro_gpu
    
    print("   Running wavelet_pro...", end=" ")
    wavelet_pro = run_wavelet(df)
    print(f"✓ {wavelet_pro['signal']}@{wavelet_pro['confidence']:.0%}")
    
    print("   Running wavelet_basic...", end=" ")
    wavelet_basic = run_wavelet_basic(df)
    print(f"✓ {wavelet_basic['signal']}@{wavelet_basic['confidence']:.0%}")
    
    print("   Running hmm...", end=" ")
    hmm = run_hmm(df)
    print(f"✓ {hmm['signal']}@{hmm['confidence']:.0%}")
    
    print("   Running lstm...", end=" ")
    lstm = run_lstm(df)
    print(f"✓ {lstm['signal']}@{lstm['confidence']:.0%}")
    
    print("   Running tft...", end=" ")
    tft = run_tft(df)
    print(f"✓ {tft['signal']}@{tft['confidence']:.0%}")
    
    print("   Running genetic...", end=" ")
    genetic = run_genetic(df)
    print(f"✓ {genetic['signal']}@{genetic['confidence']:.0%}")
    
    print("   Running hmm_pro_gpu...", end=" ")
    hmm_pro = run_hmm_pro_gpu(df)
    print(f"✓ {hmm_pro['signal']}@{hmm_pro['confidence']:.0%}")
    
    individual = {
        "wavelet_pro": wavelet_pro,
        "wavelet_basic": wavelet_basic,
        "hmm": hmm,
        "lstm": lstm,
        "tft": tft,
        "genetic": genetic,
        "hmm_pro": hmm_pro,
    }
    
    print("   Running ensemble...", end=" ")
    ensemble = run_ensemble(individual, "GROWTH", {"dxy_momentum": 0.5, "yield_momentum": -0.3})
    print(f"✓ {ensemble['signal']}@{ensemble['confidence']:.0%}\n")
    
    # Log the cycle
    print("3. Logging prediction cycle...")
    from src.paper_trading.prediction_logger import log_prediction_cycle
    
    current_price = float(df["close"].iloc[-1])
    regime = "GROWTH"
    
    all_signals = {**individual, "ensemble": ensemble}
    log_prediction_cycle(
        price=current_price,
        regime=regime,
        all_signals=all_signals,
        kelly_fraction=0.25,
        trade_taken=False
    )
    print("   ✓ Logged to CSV\n")
    
    # Display results
    print("="*100)
    print("SAMPLE DATA - All 8 Models")
    print("="*100 + "\n")
    
    print(f"Price: ${current_price:.2f}")
    print(f"Regime: {regime}\n")
    
    print("Model Results:")
    for model_name, signal_data in all_signals.items():
        signal = signal_data['signal']
        confidence = signal_data['confidence']
        print(f"  {model_name:15} | {signal:5} @ {confidence:.1%}")
    
    print("\n" + "="*100)
    print("✅ SAMPLE DATA GENERATED - Dashboard should now show all 8 models")
    print("="*100 + "\n")
    
    print("Next Steps:")
    print("  1. Go to http://localhost:5173/prediction-log")
    print("  2. You should see all 8 models with their signals")
    print("  3. Columns: WVP | WVB | HMM | LSTM | TFT | GEN | HMP | ENS\n")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
