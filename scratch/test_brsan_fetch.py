import requests, os

def check_symbol_on_pa(sym):
    s = requests.Session()
    s.proxies = {"http": "http://proxy.server:3128", "https": "http://proxy.server:3128"}
    
    # 1. Test yfinance with proxy
    import yfinance as yf
    try:
        t = yf.Ticker(sym, session=s)
        hist = t.history(period="5d", interval="1d")
        print(f"Ticker {sym} rows:", len(hist))
    except Exception as e:
        print(f"Ticker error {sym}:", e)
        
    try:
        raw = yf.download(sym, period="5d", interval="1d", session=s, progress=False)
        print(f"Download {sym} rows:", len(raw))
    except Exception as e:
        print(f"Download error {sym}:", e)

if __name__ == "__main__":
    check_symbol_on_pa("BRSAN.IS")
