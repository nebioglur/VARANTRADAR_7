import pandas as pd
import yfinance as yf
from datetime import datetime
import uuid
import threading
import time
import json

class OutcomeEngine:
    """
    V8 Outcome & Learning Engine
    Üretilen sinyallerin gelecekteki (T+5m, T+15m, vb.) performansını takip eder
    ve makine öğrenmesi modelleri için 'geribildirim' veritabanı oluşturur (DNA Snapshot).
    """
    def __init__(self):
        pass

    def register_signal(self, symbol: str, entry_price: float, breakout_data: dict, execution_data: dict, regime: str):
        """
        Yeni bir sinyali veritabanına DNA (Snapshot) ile birlikte kaydeder.
        """
        from v8_engine.database import V8Database
        
        signal_id = str(uuid.uuid4())
        
        # DNA Snapshot (Makine Öğrenmesi için kullanılacak Feature'lar)
        features = {
            "breakout_score": breakout_data.get("breakout_score", 0),
            "fakeout_risk": breakout_data.get("fakeout_risk", 0),
            "rsi": breakout_data.get("metrics", {}).get("rsi", 50),
            "relative_volume": breakout_data.get("metrics", {}).get("relative_volume", 1),
            "entry_status": execution_data.get("entry_status", "UNKNOWN"),
        }
        
        signal_data = {
            "signal_id": signal_id,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "strategy": "V8_BREAKOUT",
            "market_regime": regime,
            "score": breakout_data.get("breakout_score", 0),
            "entry_price": float(entry_price),
            "stop_price": float(entry_price * 0.95), # Default %5 risk
            "target1": float(entry_price * 1.03),    # Default %3 hedef
            "target2": float(entry_price * 1.05),    # Default %5 hedef
            "features_snapshot": features,
            "status": "ACTIVE"
        }
        
        V8Database.save_signal(signal_data)
        
        # Initialize outcome row
        try:
            conn = V8Database.get_connection()
            c = conn.cursor()
            c.execute('''
                INSERT OR IGNORE INTO v8_outcomes (signal_id, max_favorable_excursion, max_adverse_excursion, final_result)
                VALUES (?, 0.0, 0.0, 'PENDING')
            ''', (signal_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[V8 Outcome Engine] DB Init Error: {e}")
            
        return signal_id

    def run_outcome_tracker_loop(self):
        """
        Arka planda çalışan sonuç takip döngüsü (5 dakikada bir çalışır).
        Veritabanındaki ACTIVE sinyalleri tarar ve güncel fiyatlarına göre T+5, T+15 sonuçlarını yazar.
        """
        def _tracker():
            from v8_engine.database import V8Database
            while True:
                try:
                    conn = V8Database.get_connection()
                    cursor = conn.cursor()
                    
                    # Sadece son 1 gün içindeki ACTIVE sinyalleri çek
                    cursor.execute("SELECT * FROM v8_signals WHERE status='ACTIVE' AND timestamp >= datetime('now', '-1 day')")
                    active_signals = cursor.fetchall()
                    
                    if not active_signals:
                        conn.close()
                        time.sleep(300)
                        continue
                        
                    # İlgili hisselerin anlık fiyatlarını çek
                    symbols = list(set([s['symbol'] for s in active_signals]))
                    data = yf.download(symbols, period="1d", interval="1m", group_by='ticker', progress=False)
                    
                    now = datetime.now()
                    
                    for sig in active_signals:
                        sig_id = sig['signal_id']
                        sym = sig['symbol']
                        sig_time = datetime.fromisoformat(sig['timestamp'])
                        entry_price = float(sig['entry_price'])
                        
                        elapsed_mins = (now - sig_time).total_seconds() / 60.0
                        
                        try:
                            if len(symbols) == 1:
                                df = data.dropna(how='all').copy()
                            else:
                                if hasattr(data.columns, 'levels') and sym in data.columns.levels[0]:
                                    df = data[sym].dropna(how='all').copy()
                                else:
                                    continue
                                    
                            if df.empty: continue
                            
                            current_price = float(df['Close'].iloc[-1])
                            
                            cursor.execute("SELECT * FROM v8_outcomes WHERE signal_id=?", (sig_id,))
                            outcome = cursor.fetchone()
                            
                            t5 = outcome['t_5m_price'] if (outcome is not None and outcome['t_5m_price'] is not None) else (current_price if 5 <= elapsed_mins < 15 else None)
                            t15 = outcome['t_15m_price'] if (outcome is not None and outcome['t_15m_price'] is not None) else (current_price if 15 <= elapsed_mins < 30 else None)
                            t30 = outcome['t_30m_price'] if (outcome is not None and outcome['t_30m_price'] is not None) else (current_price if 30 <= elapsed_mins < 60 else None)
                            t60 = outcome['t_60m_price'] if (outcome is not None and outcome['t_60m_price'] is not None) else (current_price if 60 <= elapsed_mins < 120 else None)
                            
                            mfe = outcome['max_favorable_excursion'] if (outcome is not None and outcome['max_favorable_excursion'] is not None) else 0.0
                            mae = outcome['max_adverse_excursion'] if (outcome is not None and outcome['max_adverse_excursion'] is not None) else 0.0
                            
                            # Fiyat değişimi
                            pct_change = ((current_price - entry_price) / entry_price) * 100
                            if pct_change > mfe: mfe = pct_change
                            if pct_change < mae: mae = pct_change
                            
                            status_update = "ACTIVE"
                            # Sinyal yaşlandıkça kapat (örn: 4 saat)
                            if elapsed_mins > 240: 
                                status_update = "CLOSED"
                            
                            # Outcome kaydet/güncelle
                            # Not: SQLite3 ON CONFLICT UPSERT yontemi
                            cursor.execute('''
                                INSERT INTO v8_outcomes (signal_id, t_5m_price, t_15m_price, t_30m_price, t_60m_price, max_favorable_excursion, max_adverse_excursion, final_result)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(signal_id) DO UPDATE SET
                                t_5m_price=COALESCE(v8_outcomes.t_5m_price, excluded.t_5m_price),
                                t_15m_price=COALESCE(v8_outcomes.t_15m_price, excluded.t_15m_price),
                                t_30m_price=COALESCE(v8_outcomes.t_30m_price, excluded.t_30m_price),
                                t_60m_price=COALESCE(v8_outcomes.t_60m_price, excluded.t_60m_price),
                                max_favorable_excursion=excluded.max_favorable_excursion,
                                max_adverse_excursion=excluded.max_adverse_excursion,
                                final_result=excluded.final_result
                            ''', (sig_id, t5, t15, t30, t60, mfe, mae, status_update))
                            
                            if status_update == "CLOSED":
                                cursor.execute("UPDATE v8_signals SET status='CLOSED' WHERE signal_id=?", (sig_id,))
                                
                            conn.commit()
                        except Exception as e_inner:
                            print(f"[Outcome Engine] Error processing symbol {sym}: {e_inner}")
                            
                    conn.close()
                except Exception as e:
                    print(f"[Outcome Engine] Global tracker error: {e}")
                
                time.sleep(300) # Her 5 dakikada bir kontrol et
                
        # Start thread
        t = threading.Thread(target=_tracker, daemon=True)
        t.start()
        print("[V8] Outcome & Learning Tracker Thread Started.")
