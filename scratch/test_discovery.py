import sys
import os
import yfinance as yf

# Ensure the parent directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v8_engine.discovery import DiscoveryEngine

print('Initializing Discovery Engine...')
engine = DiscoveryEngine()

test_symbols = ["THYAO.IS", "GARAN.IS", "ISCTR.IS", "BIMAS.IS", "TUPRS.IS"]
print(f"Downloading data for {test_symbols}...")

data = yf.download(test_symbols, period="3mo", interval="1d", group_by='ticker', progress=False)

for sym in test_symbols:
    try:
        if hasattr(data.columns, 'levels'):
            df = data[sym].dropna(how='all')
        else:
            df = data.dropna(how='all')
            
        res = engine.analyze_preparation(df, sym)
        print(f"\n--- {sym} ---")
        print(f"Score: {res['preparation_score']} | State: {res['state']}")
        print(f"Reasons: {res['reasons']}")
        print(f"Metrics: {res['metrics']}")
    except Exception as e:
        print(f"Error analyzing {sym}: {e}")
