import yfinance as yf
df = yf.Ticker("DUNYH.IS").history(period="1mo")
if not df.empty:
    with open("vol_test.txt", "w") as f:
        f.write(f"Mean vol: {df['Volume'].mean()}\n")
        f.write(f"Today vol: {df['Volume'].iloc[-1]}\n")
