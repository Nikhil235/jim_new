import yfinance as yf
tickers = "GC=F PAXG-USD"
df_all = yf.download(tickers, period="1d", interval="1m", group_by="ticker", progress=False)
print("Columns:", df_all.columns)
if "GC=F" in df_all.columns.levels[0]:
    print("GC=F is in levels")
else:
    print("GC=F is MISSING")
