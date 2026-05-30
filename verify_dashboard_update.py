#!/usr/bin/env python3
"""Verify Dashboard Update - All 8 Models Logging"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

print("\n" + "="*100)
print("DASHBOARD UPDATE VERIFICATION - All 8 Models Logging")
print("="*100 + "\n")

import csv
from src.paper_trading.prediction_logger import get_csv_path

# Check CSV header
csv_path = get_csv_path()
print(f"CSV Path: {csv_path}")
print(f"CSV Exists: {os.path.exists(csv_path)}\n")

if os.path.exists(csv_path):
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = list(reader)
    
    print("CSV Header (columns):")
    print("-" * 100)
    for i, col in enumerate(header, 1):
        print(f"  {i:2d}. {col}")
    
    print(f"\nTotal Columns: {len(header)}")
    print(f"Total Rows (historical): {len(rows)}")
    
    # Check for all 8 models
    model_fields = {
        "wavelet_pro": ["wavelet_pro_signal", "wavelet_pro_conf"],
        "wavelet_basic": ["wavelet_basic_signal", "wavelet_basic_conf"],
        "hmm": ["hmm_signal", "hmm_conf"],
        "lstm": ["lstm_signal", "lstm_conf"],
        "tft": ["tft_signal", "tft_conf"],
        "genetic": ["genetic_signal", "genetic_conf"],
        "hmm_pro": ["hmm_pro_signal", "hmm_pro_conf"],
        "ensemble": ["ensemble_signal", "ensemble_conf"],
    }
    
    print("\n" + "-" * 100)
    print("Model Field Verification")
    print("-" * 100)
    
    all_models_present = True
    for model, fields in model_fields.items():
        signal_field, conf_field = fields
        has_signal = signal_field in header
        has_conf = conf_field in header
        status = "✅" if (has_signal and has_conf) else "❌"
        print(f"{status} {model:15} | {signal_field:20} | {conf_field:15} | {has_signal and has_conf}")
        if not (has_signal and has_conf):
            all_models_present = False
    
    print("\n" + "-" * 100)
    print("Sample Data (Latest 3 rows)")
    print("-" * 100)
    
    if rows:
        for i, row in enumerate(rows[-3:], 1):
            print(f"\nRow {len(rows) - 3 + i}:")
            print(f"  Timestamp: {row.get('timestamp')}")
            print(f"  Price: {row.get('price')}")
            print(f"  Regime: {row.get('regime')}")
            print(f"  Models:")
            for model in model_fields.keys():
                sig_field = f"{model}_signal"
                conf_field = f"{model}_conf"
                sig = row.get(sig_field, "N/A")
                conf = row.get(conf_field, "N/A")
                print(f"    {model:15} | {sig:5} @ {conf:5}%")
            print(f"  Kelly: {row.get('kelly_fraction')}")
            print(f"  Trade: {row.get('trade_taken')}")
            print(f"  P&L: {row.get('pnl')}")
    else:
        print("No data rows yet. Run live trader to generate logs.")
    
    # Final status
    print("\n" + "="*100)
    if all_models_present:
        print("✅ VERIFICATION PASSED - All 8 Models Present in CSV")
        print("✅ Dashboard should display: WVP | WVB | HMM | LSTM | TFT | GEN | HMP | ENS")
    else:
        print("❌ VERIFICATION FAILED - Some models missing from CSV header")
    print("="*100 + "\n")
else:
    print("❌ CSV file not found. Run live trader first to generate logs.")
