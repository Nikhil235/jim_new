import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

def fetch_data(ticker, period="1y", interval="1d"):
    print(f"Fetching {ticker} data (Period: {period}, Interval: {interval})...")
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.dropna(inplace=True)
    return df

def run_trend_following():
    """
    1. Trend Following (Daily)
    - Identify direction using 50 EMA and 200 EMA
    - Enter on pullbacks to the 50 EMA
    - R:R = 1:3
    """
    print("\n" + "="*50)
    print(" STRATEGY 1: TREND FOLLOWING (Daily)")
    print("="*50)
    df = fetch_data("GC=F", period="5y", interval="1d")
    
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    trades = []
    in_trade = False
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    
    for i in range(200, len(df)):
        price = float(df['Close'].iloc[i])
        low = float(df['Low'].iloc[i])
        high = float(df['High'].iloc[i])
        ema50 = float(df['EMA_50'].iloc[i])
        ema200 = float(df['EMA_200'].iloc[i])
        
        # Check active trade
        if in_trade:
            if low <= stop_loss:
                trades.append({"type": "LONG", "entry": entry_price, "exit": stop_loss, "pnl": stop_loss - entry_price, "result": "LOSS"})
                in_trade = False
            elif high >= take_profit:
                trades.append({"type": "LONG", "entry": entry_price, "exit": take_profit, "pnl": take_profit - entry_price, "result": "WIN"})
                in_trade = False
            continue
            
        # Long Setup: Price > 50 EMA > 200 EMA
        if ema50 > ema200 and price > ema200:
            # Pullback condition: Price touches/dips near 50 EMA but closes above it
            prev_low = float(df['Low'].iloc[i-1])
            prev_close = float(df['Close'].iloc[i-1])
            
            if prev_low < ema50 and prev_close > ema50 and price > prev_close:
                in_trade = True
                entry_price = price
                # Stop loss below recent swing low
                stop_loss = min(float(df['Low'].iloc[i-1]), float(df['Low'].iloc[i-2])) - 2.0
                risk = entry_price - stop_loss
                take_profit = entry_price + (risk * 3) # 1:3 R:R
                
    print_results(trades, "Trend Following (Daily)")


def run_gold_silver_ratio():
    """
    4. Gold/Silver Ratio Trade
    - When ratio is high (80+) -> Buy Silver
    - When ratio is low (50-) -> Buy Gold
    """
    print("\n" + "="*50)
    print(" STRATEGY 4: GOLD/SILVER RATIO (Daily)")
    print("="*50)
    gold = fetch_data("GC=F", period="10y", interval="1d")
    silver = fetch_data("SI=F", period="10y", interval="1d")
    
    # Align dates
    common_idx = gold.index.intersection(silver.index)
    gold = gold.loc[common_idx]
    silver = silver.loc[common_idx]
    
    ratio = gold['Close'] / silver['Close']
    
    trades = []
    in_trade = False
    trade_type = None # 'LONG_SILVER' or 'LONG_GOLD'
    entry_ratio = 0
    entry_gold = 0
    entry_silver = 0
    
    for i in range(len(ratio)):
        current_ratio = float(ratio.iloc[i])
        g_price = float(gold['Close'].iloc[i])
        s_price = float(silver['Close'].iloc[i])
        
        if in_trade:
            # Exit when ratio reverts to mean (~65)
            if trade_type == 'LONG_SILVER' and current_ratio <= 65:
                # Calculate PnL (Simplified percentage return)
                s_ret = (s_price - entry_silver) / entry_silver
                g_ret = (entry_gold - g_price) / entry_gold # Short gold
                pnl_pct = (s_ret + g_ret) * 100
                trades.append({"type": trade_type, "entry": entry_ratio, "exit": current_ratio, "pnl": pnl_pct, "result": "WIN" if pnl_pct > 0 else "LOSS"})
                in_trade = False
            elif trade_type == 'LONG_GOLD' and current_ratio >= 65:
                g_ret = (g_price - entry_gold) / entry_gold
                s_ret = (entry_silver - s_price) / entry_silver # Short silver
                pnl_pct = (g_ret + s_ret) * 100
                trades.append({"type": trade_type, "entry": entry_ratio, "exit": current_ratio, "pnl": pnl_pct, "result": "WIN" if pnl_pct > 0 else "LOSS"})
                in_trade = False
            continue
            
        # Entry Logic
        if current_ratio >= 80:
            in_trade = True
            trade_type = 'LONG_SILVER'
            entry_ratio = current_ratio
            entry_gold = g_price
            entry_silver = s_price
        elif current_ratio <= 50:
            in_trade = True
            trade_type = 'LONG_GOLD'
            entry_ratio = current_ratio
            entry_gold = g_price
            entry_silver = s_price
            
    print_results(trades, "Gold/Silver Ratio Reversion", is_pct=True)


def run_session_open():
    """
    5. Session Open Strategy (London Open)
    - Mark high/low of Asian session (3:30 AM - 1:30 PM IST / 22:00 - 08:00 UTC)
    - Trade breakout at London Open (08:00 UTC)
    """
    print("\n" + "="*50)
    print(" STRATEGY 5: SESSION OPEN (15m)")
    print("="*50)
    df = fetch_data("GC=F", period="60d", interval="15m")
    
    trades = []
    asian_high = 0
    asian_low = float('inf')
    in_trade = False
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    trade_dir = ""
    
    for i in range(1, len(df)):
        dt = df.index[i]
        price = float(df['Close'].iloc[i])
        high = float(df['High'].iloc[i])
        low = float(df['Low'].iloc[i])
        
        # UTC hours
        hour = dt.hour
        
        # Asian Session (22:00 to 07:59 UTC)
        if hour >= 22 or hour < 8:
            asian_high = max(asian_high, high)
            asian_low = min(asian_low, low)
            in_trade = False # Reset daily trade
            
        # London Open (08:00 to 12:00 UTC)
        elif hour >= 8 and hour <= 12 and not in_trade and asian_high > 0:
            # Check Breakout
            if price > asian_high:
                in_trade = True
                trade_dir = "LONG"
                entry_price = price
                stop_loss = asian_low # Stop behind the range
                risk = entry_price - stop_loss
                take_profit = entry_price + (risk * 2) # 1:2 R:R
            elif price < asian_low:
                in_trade = True
                trade_dir = "SHORT"
                entry_price = price
                stop_loss = asian_high
                risk = stop_loss - entry_price
                take_profit = entry_price - (risk * 2)
                
        # Manage active trade
        elif in_trade:
            if trade_dir == "LONG":
                if low <= stop_loss:
                    trades.append({"type": "LONG", "entry": entry_price, "exit": stop_loss, "pnl": stop_loss - entry_price, "result": "LOSS"})
                    in_trade = False
                elif high >= take_profit:
                    trades.append({"type": "LONG", "entry": entry_price, "exit": take_profit, "pnl": take_profit - entry_price, "result": "WIN"})
                    in_trade = False
            else: # SHORT
                if high >= stop_loss:
                    trades.append({"type": "SHORT", "entry": entry_price, "exit": stop_loss, "pnl": entry_price - stop_loss, "result": "LOSS"})
                    in_trade = False
                elif low <= take_profit:
                    trades.append({"type": "SHORT", "entry": entry_price, "exit": take_profit, "pnl": entry_price - take_profit, "result": "WIN"})
                    in_trade = False
                    
        # End of day cleanup
        if hour == 21:
            asian_high = 0
            asian_low = float('inf')
            
    print_results(trades, "London Session Breakout")


def print_results(trades, name, is_pct=False):
    print(f"\n--- Results for {name} ---")
    if not trades:
        print("No trades triggered in this historical period.")
        return
        
    wins = [t for t in trades if t['result'] == 'WIN']
    losses = [t for t in trades if t['result'] == 'LOSS']
    win_rate = len(wins) / len(trades) * 100
    
    total_pnl = sum(t['pnl'] for t in trades)
    
    print(f"Total Trades: {len(trades)}")
    print(f"Win Rate:     {win_rate:.1f}% ({len(wins)}W / {len(losses)}L)")
    if is_pct:
        print(f"Total P&L:    {total_pnl:+.2f}%")
    else:
        print(f"Total P&L:    ${total_pnl:+.2f} per ounce")
    print("-" * 30)
    for i, t in enumerate(trades[-5:]):
        unit = "%" if is_pct else "$"
        print(f"Trade {len(trades)-4+i}: {t['type']} | Entry: {t['entry']:.2f} | Exit: {t['exit']:.2f} | P&L: {t['pnl']:+.2f}{unit} ({t['result']})")

if __name__ == "__main__":
    print("="*60)
    print(" GOLD & SILVER STRATEGY BACKTESTING SIMULATOR")
    print("="*60)
    print("1. Trend Following (Daily, 50/200 EMA, 1:3 R:R)")
    print("2. Gold/Silver Ratio Trade (Daily, Hedged Pairs)")
    print("3. Session Open Breakout (15m, London Open, 1:2 R:R)")
    print("="*60)
    
    choice = input("Select a strategy to run (1-3): ")
    
    if choice == "1":
        run_trend_following()
    elif choice == "2":
        run_gold_silver_ratio()
    elif choice == "3":
        run_session_open()
    else:
        print("Invalid choice. Please run again and select 1, 2, or 3.")
