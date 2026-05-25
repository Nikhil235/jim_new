import yfinance as yf
from datetime import datetime

tickers = ["PAXG-USD", "XAUT-USD"]
for t in tickers:
    ticker = yf.Ticker(t)
    df = ticker.history(period="1d", interval="1m")
    print(f"\n--- {t} ---")
    if not df.empty:
        print(f"Latest time: {df.index[-1]}")
        print(df.tail(2))
    else:
        print("Empty dataframe")
