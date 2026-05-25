import yfinance as yf
from datetime import datetime
ticker = yf.Ticker("GC=F")
df = ticker.history(period="5d", interval="1m")
print(f"Current local time: {datetime.now()}")
if not df.empty:
    print(f"Latest GC=F data time: {df.index[-1]}")
    print(df.tail(5))
else:
    print("Empty dataframe for GC=F")
