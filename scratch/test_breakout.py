import sys
import os
import yfinance as yf

# Ensure the parent directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v8_engine.breakout import BreakoutEngine

print('Initializing Breakout Engine...')
engine = BreakoutEngine()

test_symbols = ["THYAO.IS", "BIMAS.IS", "TUPRS.IS"]
print(f"Downloading data for {test_symbols}...")

data = yf.download(test_symbols, period="3mo", interval="1d", group_by='ticker', progress=False)

for sym in test_symbols:
    try:
        if hasattr(data.columns, 'levels'):
            df = data[sym].dropna(how='all')
        else:
            df = data.dropna(how='all')
            
        res = engine.analyze_breakout(df, sym, "NEUTRAL")
        print(f"\n--- {sym} ---")
        print(f"Is Breakout: {res['is_breakout']} | Status: {res['status']}")
        print(f"Breakout Score: {res['breakout_score']} | Fakeout Risk: {res['fakeout_risk']}")
        print(f"Reasons: {res['reasons']}")
        print(f"Metrics: {res['metrics']}")
    except Exception as e:
        print(f"Error analyzing {sym}: {e}")
