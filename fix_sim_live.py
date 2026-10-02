from services.simulation_engine import SimulationEngine
from services.market_data import MarketDataManager
from datetime import datetime
import yfinance as yf
import pandas as pd

today_str = datetime.now().strftime("%Y-%m-%d")

# 1. Download 5m data manually and inject it to market_data DB!
signals = MarketDataManager.get_signals(today_str)
symbols = [s['symbol'] for s in signals]
if symbols:
    print(f"Downloading 5m data for {len(symbols)} symbols...")
    data = yf.download(symbols, period="5d", interval="5m", group_by='ticker', threads=False, progress=False)
    conn = MarketDataManager._get_conn()
    cursor = conn.cursor()
    for sym in symbols:
        df = data if len(symbols) == 1 else data[sym]
        df = df.dropna(subset=['Close'])
        for idx, row in df.iterrows():
            timestamp_str = str(idx)
            try:
                cursor.execute("""
                    INSERT INTO market_data (date_str, timestamp, symbol, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(timestamp, symbol) DO NOTHING
                """, (today_str, timestamp_str, sym, float(row['Open']), float(row['High']), float(row['Low']), float(row['Close']), float(row['Volume'])))
            except:
                pass
    conn.commit()
    conn.close()
    print("Market data inserted to DB.")

# 2. Run simulation
sim = SimulationEngine(owner="local:nebioglur")
sim.run_daily_simulation(today_str)
print("Simulation completed!")
