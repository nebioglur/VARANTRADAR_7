import yfinance as yf
from datetime import datetime

d_str = datetime.now().strftime("%Y-%m-%d")
data = yf.download(["AKFIS.IS"], period="1d", interval="5m", progress=False)

if not data.empty:
    for idx_time, row in data.iterrows():
        idx_date = idx_time.strftime("%Y-%m-%d")
        print(idx_time, "->", idx_date, "match?", idx_date == d_str)
