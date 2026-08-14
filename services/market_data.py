import yfinance as yf
import pandas as pd
from datetime import datetime
import time
import json
from services.trade_database import get_connection

class MarketDataManager:
    
    @staticmethod
    def record_signals(date_str: str, candidates: list):
        """
        10:00 - 10:15 arasında bulunan Tavan Adaylarını (Sinyalleri) veritabanına yazar.
        """
        conn = get_connection()
        cursor = conn.cursor()
        for cand in candidates:
            sym = cand.get('symbol', '')
            if not sym:
                continue
            
            # .IS uzantısı garantile
            if not sym.endswith('.IS'):
                sym += '.IS'
                
            score = float(cand.get('Score', 0))
            morning_price = float(cand.get('morning_price', 0))
            ceiling_target = float(cand.get('ceiling_target', 0))
            morning_phase = cand.get('morning_phase', '')
            metadata = json.dumps(cand, ensure_ascii=False)
            
            try:
                cursor.execute("""
                    INSERT INTO signals (date_str, symbol, score, morning_price, ceiling_target, morning_phase, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(date_str, symbol) DO UPDATE SET 
                        score=excluded.score, 
                        morning_price=excluded.morning_price,
                        ceiling_target=excluded.ceiling_target,
                        morning_phase=excluded.morning_phase,
                        metadata=excluded.metadata
                """, (date_str, sym, score, morning_price, ceiling_target, morning_phase, metadata))
            except Exception as e:
                print(f"[MarketData] Sinyal kayıt hatası {sym}: {e}")
                
        conn.commit()
        conn.close()

    @staticmethod
    def fetch_and_store_intraday(date_str: str):
        """
        O gün sinyal üretilen tüm hisseler için yfinance'den 5 dakikalık veya 1 saatlik
        geçmişi indirir ve market_data tablosuna yazar.
        Simülasyon motoru buradan okuyacaktır.
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT symbol FROM signals WHERE date_str = ?", (date_str,))
        rows = cursor.fetchall()
        symbols = [r["symbol"] for r in rows]
        
        if not symbols:
            conn.close()
            return
            
        print(f"[MarketData] {date_str} için {len(symbols)} hissenin 5m verisi indiriliyor...")
        
        # Yahoo Finance bazen 5m vermeyebilir eski tarihler için, 1mo içinde verir.
        try:
            # interval = 5m
            data = yf.download(symbols, period="1mo", interval="5m", group_by='ticker', threads=False, progress=False)
            
            # Parsing yfinance dataframe
            for sym in symbols:
                if len(symbols) == 1:
                    df = data
                else:
                    if hasattr(data.columns, 'levels') and sym in data.columns.levels[0]:
                        df = data[sym]
                    else:
                        continue
                        
                df = df.dropna(how='all')
                if df.empty:
                    continue
                    
                for idx_time, row in df.iterrows():
                    # idx_time timezone aware datetime
                    idx_date = idx_time.strftime("%Y-%m-%d")
                    # Sadece ilgili günün verisini kaydet
                    if idx_date != date_str:
                        continue
                        
                    timestamp_str = str(idx_time)
                    _open = float(row['Open'])
                    _high = float(row['High'])
                    _low = float(row['Low'])
                    _close = float(row['Close'])
                    _vol = float(row['Volume'])
                    
                    try:
                        cursor.execute("""
                            INSERT INTO market_data (date_str, timestamp, symbol, open, high, low, close, volume)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(timestamp, symbol) DO NOTHING
                        """, (date_str, timestamp_str, sym, _open, _high, _low, _close, _vol))
                    except Exception as e:
                        pass
        except Exception as e:
            print(f"[MarketData] YF indirme hatası: {e}")
            
        conn.commit()
        conn.close()

    @staticmethod
    def get_signals(date_str: str) -> list:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM signals WHERE date_str = ? ORDER BY score DESC", (date_str,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_market_data(date_str: str, symbol: str) -> pd.DataFrame:
        """
        Backtester için veritabanından Pandas DataFrame döndürür.
        """
        conn = get_connection()
        df = pd.read_sql_query("""
            SELECT timestamp as Datetime, open as Open, high as High, low as Low, close as Close, volume as Volume 
            FROM market_data 
            WHERE date_str = ? AND symbol = ? 
            ORDER BY timestamp ASC
        """, conn, params=(date_str, symbol))
        conn.close()
        
        if not df.empty:
            df['Datetime'] = pd.to_datetime(df['Datetime'])
            df.set_index('Datetime', inplace=True)
            
        return df
