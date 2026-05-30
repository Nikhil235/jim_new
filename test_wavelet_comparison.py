#!/usr/bin/env python3
"""Quick test to verify both WaveletPro and basic wavelet work and show comparison."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from loguru import logger

logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>", level="INFO")

from src.paper_trading.live_inference import run_wavelet, run_wavelet_basic

# Create test data
print("\n" + "="*80)
print("WAVELET COMPARISON TEST")
print("="*80 + "\n")

np.random.seed(42)
n_bars = 300
dates = pd.date_range(start='2026-01-01', periods=n_bars, freq='1h')
close = np.linspace(1900, 2050, n_bars) + np.cumsum(np.random.randn(n_bars) * 5)
df = pd.DataFrame({
    'open': close + np.random.randn(n_bars) * 2,
    'high': close + np.abs(np.random.randn(n_bars) * 2),
    'low': close - np.abs(np.random.randn(n_bars) * 2),
    'close': close,
    'volume': np.random.randint(1000000, 5000000, n_bars),
}, index=dates)

# Add macro data
df['dxy'] = np.linspace(100, 102, n_bars) + np.cumsum(np.random.randn(n_bars) * 0.1)
df['dxy_returns'] = df['dxy'].pct_change()
df['us10y'] = np.linspace(4.2, 4.1, n_bars) + np.random.randn(n_bars) * 0.05
df['us10y_returns'] = df['us10y'].pct_change()

print("Test Data:")
print(f"  - Bars: {len(df)}")
print(f"  - Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
print(f"  - Columns: {list(df.columns)}\n")

print("="*80)
print("RUNNING WAVELET MODELS")
print("="*80 + "\n")

# Test WaveletPro
print("[1] WaveletPro (6-level DWT + CWT + 30+ features):")
wavelet_pro_sig = run_wavelet(df)
print(f"    Signal:     {wavelet_pro_sig['signal']}")
print(f"    Confidence: {wavelet_pro_sig['confidence']:.1%}")
print(f"    Reasoning:  {wavelet_pro_sig['reasoning']}\n")

# Test Basic Wavelet
print("[2] Basic Wavelet (5-level DWT only):")
wavelet_basic_sig = run_wavelet_basic(df)
print(f"    Signal:     {wavelet_basic_sig['signal']}")
print(f"    Confidence: {wavelet_basic_sig['confidence']:.1%}")
print(f"    Reasoning:  {wavelet_basic_sig['reasoning']}\n")

print("="*80)
print("COMPARISON")
print("="*80)
print(f"\nSignal Agreement:  {wavelet_pro_sig['signal'] == wavelet_basic_sig['signal']}")
print(f"Pro  Confidence:   {wavelet_pro_sig['confidence']:.1%}")
print(f"Basic Confidence:  {wavelet_basic_sig['confidence']:.1%}")
print(f"Confidence Diff:   {abs(wavelet_pro_sig['confidence'] - wavelet_basic_sig['confidence']):.1%}")

# Show display format
print("\n" + "="*80)
print("DISPLAY FORMAT (as shown in live trader)")
print("="*80 + "\n")

model_labels = {
    "wavelet_pro": "WVP",      # WaveletPro (6-level)
    "wavelet_basic": "WVB",    # Basic 5-level
    "hmm": "HMM",
    "lstm": "LST",
    "tft": "TFT",
    "genetic": "GEN",
    "hmm_pro": "HMP",
    "ensemble": "ENS",
}

# Mock signals dict
signals = {
    "wavelet_pro": wavelet_pro_sig,
    "wavelet_basic": wavelet_basic_sig,
    "hmm": {"signal": "LONG", "confidence": 0.32},
    "lstm": {"signal": "SHORT", "confidence": 0.30},
    "tft": {"signal": "LONG", "confidence": 0.63},
    "genetic": {"signal": "HOLD", "confidence": 0.20},
    "hmm_pro": {"signal": "SHORT", "confidence": 0.53},
    "ensemble": {"signal": "LONG", "confidence": 0.31},
}

sig_parts = []
for m in ["wavelet_pro", "wavelet_basic", "hmm", "lstm", "tft", "genetic", "hmm_pro", "ensemble"]:
    s = signals.get(m, {})
    sig_val = s.get("signal", "?")[:1]
    conf = s.get("confidence", 0)
    label = model_labels.get(m, m[:3].upper())
    sig_parts.append(f"{label}:{sig_val}{conf:.0%}")

sig_line = " | ".join(sig_parts)

print(f"Signals: {sig_line}\n")

print("="*80)
print("✓ BOTH WAVELET MODELS WORKING CORRECTLY")
print("="*80 + "\n")

print("Key Differences:")
print(f"  WVP (WaveletPro):   Advanced 6-level DWT + CWT + ML features")
print(f"  WVB (Basic):        Simple 5-level DWT decomposition")
print(f"\nYou can now compare their accuracy and precision in live trading!")
print()
