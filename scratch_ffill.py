import yfinance as yf
import pandas as pd

tickers = "GC=F PAXG-USD DX-Y.NYB"
df_all = yf.download(tickers, period="5d", interval="1m", group_by="ticker", progress=False)

df = df_all["GC=F"].copy()
df_pax = df_all["PAXG-USD"].copy()

for col in ["Open", "High", "Low", "Close"]:
    df[col] = df[col].fillna(df_pax[col])
df["Volume"] = df["Volume"].fillna(df_pax["Volume"].replace(0, 1))

df["dxy"] = df_all["DX-Y.NYB"]["Close"].ffill()
df = df.dropna(subset=["Close", "dxy"])

print("Combined DataFrame tail:")
print(df[["Close", "dxy"]].tail(5))
