import yfinance as yf
ticker = yf.Ticker("GC=F")
df = ticker.history(period="5d")
print("GC=F")
print(df)
ticker = yf.Ticker("XAUUSD=X")
df = ticker.history(period="5d")
print("XAUUSD=X")
print(df)
