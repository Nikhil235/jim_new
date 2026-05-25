import yfinance as yf
ticker = yf.Ticker("PAXG-USD")
df = ticker.history(period="1d", interval="1m")
print(df["Volume"].tail(10))
