import yfinance as yf
import pandas as pd
tickers = "GC=F PAXG-USD"
df_all = yf.download(tickers, period="5d", interval="15m", group_by="ticker", progress=False)

df_gc = df_all["GC=F"].copy()
df_pax = df_all["PAXG-USD"].copy()

print("GC=F tail:")
print(df_gc.dropna().tail(2))

print("\nPAXG-USD tail:")
print(df_pax.dropna().tail(2))

# Combine
df_combined = df_gc.copy()
for col in ["Open", "High", "Low", "Close"]:
    df_combined[col] = df_combined[col].fillna(df_pax[col])

# For volume, PAXG volume might be 0, so fill with 1 to avoid the zero-volume filter
df_combined["Volume"] = df_combined["Volume"].fillna(df_pax["Volume"].replace(0, 1))
df_combined = df_combined.dropna(subset=["Close"])

print("\nCombined tail:")
print(df_combined.tail(5))
