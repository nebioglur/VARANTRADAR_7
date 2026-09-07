import pandas as pd
import yfinance as yf
from datetime import datetime
from zoneinfo import ZoneInfo
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
        Arka planda calisan sonuc takip dongusu (60 saniyede bir calisir).
        Veritabanindaki ACTIVE sinyalleri tarar ve 1m/5m/10m/15m/30m/60m/120m/240m/EOD/1d
        fiyatlarini backfill ile yazar.
        """
        def _tracker():
            from v8_engine.database import V8Database
            while True:
                try:
                    conn = V8Database.get_connection()
                    cursor = conn.cursor()
                    
                    # Sadece son 2 gun icindeki ACTIVE sinyalleri cek
                    cursor.execute("SELECT * FROM v8_signals WHERE status='ACTIVE' AND timestamp >= datetime('now', '-2 day')")
                    active_signals = cursor.fetchall()
                    
                    if not active_signals:
                        conn.close()
                        time.sleep(60)
                        continue
                        
                    # İlgili hisselerin anlik fiyatlarini cek
                    symbols = list(set([s['symbol'] for s in active_signals]))
                    data = yf.download(symbols, period="5d", interval="1m", group_by='ticker', progress=False)
                    
                    now = datetime.now()
                    
                    for sig in active_signals:
                        sig_id = sig['signal_id']
                        sym = sig['symbol']
                        sig_time = datetime.fromisoformat(sig['timestamp'])
                        # DB'den gelen zaman tz-aware olabilir; bar index'i ile kiyas icin naive Istanbul zamanina cevir
                        if sig_time.tzinfo is not None:
                            try:
                                sig_time = sig_time.astimezone(ZoneInfo("Europe/Istanbul")).replace(tzinfo=None)
                            except Exception:
                                sig_time = sig_time.replace(tzinfo=None)
                        entry_price = float(sig['entry_price'])

                        elapsed_mins = (now - sig_time).total_seconds() / 60.0

                        try:
                            if len(symbols) == 1:
                                df = data.dropna(how='all').copy()
                            else:
                                if hasattr(data.columns, 'levels') and sym in data.columns.levels[0]:
                                    df = data[sym].dropna(how='all').copy()
                                else:
                                    # Bulk veri yoksa tek sembol fallback dene
                                    try:
                                        df = yf.Ticker(sym).history(period="5d", interval="1m").dropna(how='all').copy()
                                    except Exception:
                                        continue

                            if df.empty: continue

                            # Index'i datetime'a cevir ve sirala
                            try:
                                df.index = pd.to_datetime(df.index, utc=True).tz_convert('Europe/Istanbul').tz_localize(None)
                            except Exception:
                                try:
                                    df.index = pd.to_datetime(df.index).tz_localize(None)
                                except Exception:
                                    pass
                            df = df.sort_index()

                            current_price = float(df['Close'].iloc[-1])

                            cursor.execute("SELECT * FROM v8_outcomes WHERE signal_id=?", (sig_id,))
                            outcome = cursor.fetchone()

                            def _price_at(mins_after):
                                """Hedef andan itibaren ilk mevcut barin close'u (backfill)."""
                                target_ts = sig_time + pd.Timedelta(minutes=mins_after)
                                sub = df[df.index >= target_ts]
                                if sub.empty: return None
                                return float(sub['Close'].iloc[0])

                            def _get_existing(col):
                                if outcome is None or outcome[col] is None:
                                    return None
                                return outcome[col]

                            # Kisa vadeli pencereler: 3m, 5m, 10m, 15m, 30m
                            # Orta vadeli: 60m, 120m, 240m (4h)
                            t3  = _get_existing('t_3m_price')  or (_price_at(3) if elapsed_mins >= 3 else None)
                            t5  = _get_existing('t_5m_price')  or (_price_at(5) if elapsed_mins >= 5 else None)
                            t10 = _get_existing('t_10m_price') or (_price_at(10) if elapsed_mins >= 10 else None)
                            t15 = _get_existing('t_15m_price') or (_price_at(15) if elapsed_mins >= 15 else None)
                            t30 = _get_existing('t_30m_price') or (_price_at(30) if elapsed_mins >= 30 else None)
                            t60 = _get_existing('t_60m_price') or (_price_at(60) if elapsed_mins >= 60 else None)
                            t120 = _get_existing('t_120m_price') or (_price_at(120) if elapsed_mins >= 120 else None)
                            t240 = _get_existing('t_240m_price') or (_price_at(240) if elapsed_mins >= 240 else None)

                            # EOD: ayni gun son kapanis fiyati (seans bitince dolar)
                            t_eod = _get_existing('t_eod_price')
                            if t_eod is None:
                                # Ayni gune ait tum barlarin son close'u (simdilik mevcut son)
                                same_day = df[df.index.date == sig_time.date()]
                                if not same_day.empty:
                                    t_eod = float(same_day['Close'].iloc[-1])

                            # T+1 gunku kapanis: ertesi gun son bar (varsa)
                            t_1d = _get_existing('t_1d_price')
                            if t_1d is None:
                                next_day = sig_time.date() + pd.Timedelta(days=1)
                                next_bars = df[df.index.date == next_day]
                                if not next_bars.empty:
                                    t_1d = float(next_bars['Close'].iloc[-1])

                            mfe = _get_existing('max_favorable_excursion') or 0.0
                            mae = _get_existing('max_adverse_excursion') or 0.0

                            # MFE/MAE: giristen bugunku tum barlar uzerinden
                            try:
                                entry_ts = sig_time
                                bars = df.loc[df.index >= entry_ts, 'Close']
                                if bars.empty:
                                    bars = df['Close']
                                pcts = ((bars - entry_price) / entry_price) * 100.0
                                if not pcts.empty:
                                    day_max = float(pcts.max())
                                    day_min = float(pcts.min())
                                    mfe = max(mfe, day_max)
                                    mae = min(mae, day_min)
                            except Exception:
                                pct_change = ((current_price - entry_price) / entry_price) * 100
                                if pct_change > mfe: mfe = pct_change
                                if pct_change < mae: mae = pct_change

                            status_update = "ACTIVE"
                            # Sinyal gun sonunda kapanir (seans bitisi ~18:15) ya da 6 saat
                            now_time = now.time()
                            market_closed = now_time.hour >= 18 and now_time.minute >= 15
                            if elapsed_mins > 360 or market_closed:
                                status_update = "CLOSED"

                            # Outcome kaydet/guncelle
                            cursor.execute('''
                                INSERT INTO v8_outcomes (
                                    signal_id,
                                    t_3m_price, t_5m_price, t_10m_price, t_15m_price,
                                    t_30m_price, t_60m_price, t_120m_price, t_240m_price,
                                    t_eod_price, t_1d_price,
                                    max_favorable_excursion, max_adverse_excursion, final_result
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(signal_id) DO UPDATE SET
                                t_3m_price=COALESCE(v8_outcomes.t_3m_price, excluded.t_3m_price),
                                t_5m_price=COALESCE(v8_outcomes.t_5m_price, excluded.t_5m_price),
                                t_10m_price=COALESCE(v8_outcomes.t_10m_price, excluded.t_10m_price),
                                t_15m_price=COALESCE(v8_outcomes.t_15m_price, excluded.t_15m_price),
                                t_30m_price=COALESCE(v8_outcomes.t_30m_price, excluded.t_30m_price),
                                t_60m_price=COALESCE(v8_outcomes.t_60m_price, excluded.t_60m_price),
                                t_120m_price=COALESCE(v8_outcomes.t_120m_price, excluded.t_120m_price),
                                t_240m_price=COALESCE(v8_outcomes.t_240m_price, excluded.t_240m_price),
                                t_eod_price=COALESCE(v8_outcomes.t_eod_price, excluded.t_eod_price),
                                t_1d_price=COALESCE(v8_outcomes.t_1d_price, excluded.t_1d_price),
                                max_favorable_excursion=excluded.max_favorable_excursion,
                                max_adverse_excursion=excluded.max_adverse_excursion,
                                final_result=excluded.final_result
                            ''', (sig_id, t3, t5, t10, t15, t30, t60, t120, t240, t_eod, t_1d, mfe, mae, status_update))

                            if status_update == "CLOSED":
                                # Kapanista net degisime gore kesin sonuc etiketle
                                net_pct = ((current_price - entry_price) / entry_price) * 100
                                final = "WIN" if net_pct > 0.5 else ("LOSS" if net_pct < -0.5 else "NEUTRAL")
                                cursor.execute("UPDATE v8_signals SET status='CLOSED' WHERE signal_id=?", (sig_id,))
                                cursor.execute("UPDATE v8_outcomes SET final_result=? WHERE signal_id=?", (final, sig_id))

                            conn.commit()
                        except Exception as e_inner:
                            print(f"[Outcome Engine] Error processing symbol {sym}: {e_inner}")
                            
                    conn.close()
                except Exception as e:
                    print(f"[Outcome Engine] Global tracker error: {e}")
                
                time.sleep(60)
                
        # Start thread
        t = threading.Thread(target=_tracker, daemon=True)
        t.start()
        print("[V8] Outcome & Learning Tracker Thread Started.")
