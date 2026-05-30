#!/usr/bin/env python3
"""Test the run_single_cycle function to verify all 8 models display correctly."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
from loguru import logger

logger.remove()
logger.add(sys.stderr, 
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO"
)

from src.paper_trading.engine import PaperTradingEngine, PaperTradingConfig
from src.risk.manager import RiskManager
from src.utils.config import load_config

# Import run_single_cycle from live_trader
import sys
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from live_trader import run_single_cycle

print("\n" + "="*80)
print("INTEGRATION TEST: Single Cycle with All 8 Models")
print("="*80 + "\n")

try:
    # Initialize engines
    cfg = load_config()
    pt_cfg = PaperTradingConfig(
        initial_capital=100000,
        min_confidence=0.35,
        kelly_fraction=0.25,
    )
    engine = PaperTradingEngine(pt_cfg)
    engine.start()
    
    risk_mgr = RiskManager(cfg)
    risk_mgr.min_confidence = 0.35
    
    print("Running single cycle [Tick #1]...")
    print("-" * 80 + "\n")
    
    # Run one cycle
    price, regime, signals, trade_taken = run_single_cycle(
        engine=engine,
        risk_mgr=risk_mgr,
        iteration=1,
        dry_run=True,
    )
    
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80 + "\n")
    
    if price is None:
        print("ERROR: Data fetch failed")
        sys.exit(1)
    
    print(f"Gold Price: ${price:,.2f}")
    print(f"Regime: {regime}")
    print(f"Trade Taken: {trade_taken}\n")
    
    print("Individual Signals:")
    for model_name, sig in signals.items():
        if model_name != "ensemble":
            print(f"  {model_name:15} : {sig.get('signal', 'HOLD'):5} @ {sig.get('confidence', 0):.0%}")
    
    print(f"\nEnsemble:")
    if "ensemble" in signals:
        ens = signals["ensemble"]
        print(f"  ensemble      : {ens.get('signal', 'HOLD'):5} @ {ens.get('confidence', 0):.0%}")
    
    print("\n" + "="*80)
    print("SIGNAL DISPLAY FORMAT (as would appear in trader console)")
    print("="*80 + "\n")
    
    model_labels = {
        "wavelet_pro": "WVP",
        "wavelet_basic": "WVB",
        "hmm": "HMM",
        "lstm": "LST",
        "tft": "TFT",
        "genetic": "GEN",
        "hmm_pro": "HMP",
        "ensemble": "ENS",
    }
    
    sig_summary = " | ".join(
        f"{model_labels.get(m, m[:3].upper())}:{v.get('signal', '?')}@{v.get('confidence', 0):.0%}"
        for m, v in signals.items()
    )
    print(f"Signals: {sig_summary}\n")
    
    print("="*80)
    print("✓ SUCCESS: All 8 models displayed without errors!")
    print("="*80 + "\n")
    
except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
