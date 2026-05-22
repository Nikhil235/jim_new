import requests
import json
import time

def check_engine():
    print("Connecting to Paper Trading Engine API...")
    try:
        status_res = requests.get("http://127.0.0.1:8000/paper-trading/status")
        perf_res = requests.get("http://127.0.0.1:8000/paper-trading/performance")
        
        status = status_res.json()
        perf = perf_res.json()
        
        print("\n=======================================")
        print("      LIVE ENGINE STATUS REPORT")
        print("=======================================")
        print(f"Engine Status: {'ACTIVE' if status.get('is_running') else 'STOPPED'}")
        
        print("\n[+] PORTFOLIO & PNL")
        print(f"  Current Equity: ${perf.get('current_equity', 0):,.2f}")
        print(f"  Session PnL:    ${perf.get('session_pnl', 0):,.2f}")
        
        print("\n[+] RECENT TRADES")
        trades = perf.get("recent_trades", [])
        if not trades:
            print("  No trades executed yet.")
        else:
            for t in trades[:5]:
                print(f"  {t.get('time')} | {t.get('direction')} {t.get('size')} @ ${t.get('entry_price', 0):.2f}")
                
        print("\n[+] MODEL INFERENCE")
        signals_res = requests.get("http://127.0.0.1:8000/paper-trading/live-signals")
        signals = signals_res.json()
        
        weights_res = requests.get("http://127.0.0.1:8000/paper-trading/model-weights")
        weights = weights_res.json()
        
        print(f"  Detected Regime: {weights.get('regime', 'N/A')}")
        print("\n  Active Model Weights:")
        for model, w in weights.get("weights", {}).items():
            if w > 0.05:
                # Get current signal for this model
                sig = next((s.get('signal') for s in signals if s.get('model') == model), "HOLD")
                print(f"    {model.upper():<10} | Weight: {w*100:.1f}% | Signal: {sig}")
                
        print("\n=======================================")
    except Exception as e:
        print(f"Error connecting to API: {e}")

if __name__ == "__main__":
    check_engine()
