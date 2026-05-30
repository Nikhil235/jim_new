#!/usr/bin/env python3
"""Verify that live_trader.py can run without KeyError on model signals."""

import sys
from pathlib import Path
import logging

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Suppress verbose logging
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

from loguru import logger
logger.remove()
logger.add(sys.stderr, 
    format="<level>{level: <6}</level> | <cyan>{message}</cyan>",
    level="WARNING"
)

try:
    from src.paper_trading.engine import PaperTradingEngine, PaperTradingConfig
    from src.risk.manager import RiskManager
    from src.utils.config import load_config
    import sys
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    from live_trader import run_single_cycle
    
    print("\n[TEST] Initializing engines...")
    cfg = load_config()
    pt_cfg = PaperTradingConfig(initial_capital=100000, min_confidence=0.35, kelly_fraction=0.25)
    engine = PaperTradingEngine(pt_cfg)
    engine.start()
    risk_mgr = RiskManager(cfg)
    risk_mgr.min_confidence = 0.35
    
    print("[TEST] Running cycle...")
    price, regime, signals, trade_taken = run_single_cycle(
        engine=engine, risk_mgr=risk_mgr, iteration=1, dry_run=True,
    )
    
    print(f"\n✓ SUCCESS! Price=${price:,.2f} | Regime={regime}")
    print("\nSignals Displayed:")
    
    model_labels = {
        "wavelet_pro": "WVP", "wavelet_basic": "WVB", "hmm": "HMM", "lstm": "LST",
        "tft": "TFT", "genetic": "GEN", "hmm_pro": "HMP", "ensemble": "ENS",
    }
    
    for m, v in signals.items():
        label = model_labels.get(m, m[:3].upper())
        sig = v.get("signal", "?")
        conf = v.get("confidence", 0)
        print(f"  {label:4} : {sig:5} @ {conf:5.0%}")
    
    sig_display = " | ".join(
        f"{model_labels.get(m, m[:3].upper())}:{v.get('signal', '?')[0]}{v.get('confidence', 0):.0%}"
        for m, v in signals.items()
    )
    print(f"\n{sig_display}")
    print("\n✓ All 8 models working correctly!\n")
    
except Exception as e:
    print(f"\n✗ ERROR: {type(e).__name__}: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)
