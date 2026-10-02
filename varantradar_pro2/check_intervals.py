from database.db_manager import DBManager
import pandas as pd

db = DBManager()
intervals = ["1d", "1h", "15m", "5m"]

print("=== VERITABANI KONTROLU (ASELS.IS) ===")
for interval in intervals:
    df = db.get_stock_data("ASELS.IS", interval)
    if not df.empty:
        # Sort by date
        df.sort_values('date', inplace=True)
        # Drop NaN close
        df.dropna(subset=['close'], inplace=True)
        if not df.empty:
            print(f"[{interval}] Veri Sayısı: {len(df)} | Son Tarih: {df.iloc[-1]['date']} | Son Fiyat: {df.iloc[-1]['close']}")
        else:
            print(f"[{interval}] Veri var ama geçerli fiyat yok (NaN)!")
    else:
        print(f"[{interval}] Veritabanında hiç veri yok!")
