import yfinance as yf
import pandas as pd
from datetime import datetime
import time
import json
from services.trade_database import get_connection


def _get_pa_session():
    import requests, os
    if os.path.exists("/home/varantradarpro") or "pythonanywhere" in os.environ.get("PYTHONANYWHERE_DOMAIN", "").lower() or os.path.exists("/etc/pythonanywhere"):
        s = requests.Session()
        s.proxies = {"http": "http://proxy.server:3128", "https": "http://proxy.server:3128"}
        return s
    return None

class MarketDataManager:
    _last_fetch_ts = 0
    _rate_limit_until = 0
    
    @staticmethod
    def record_signals(date_str: str, candidates: list):
        """
        10:00 - 10:15 arasında bulunan Tavan Adaylarını (Sinyalleri) veritabanına yazar.
        """
        conn = get_connection()
        cursor = conn.cursor()
        for cand in candidates:
            sym = cand.get('symbol', '') or cand.get('Symbol', '')
            if not sym:
                continue
            
            # .IS uzantısı garantile
            if not sym.endswith('.IS'):
                sym += '.IS'
                
            score = float(cand.get('Score', 0) or cand.get('score', 0))
            morning_price = float(cand.get('morning_price', 0) or cand.get('Price', 0) or cand.get('Daily_Close', 0))
            ceiling_target = float(cand.get('ceiling_target', 0) or cand.get('Ceiling_Price', 0))
            morning_phase = cand.get('morning_phase', '') or cand.get('Phase', '') or cand.get('Phase_Badge', '')
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

    @classmethod
    def fetch_and_store_intraday(cls, date_str: str, period: str = "5d"):
        """
        O gün sinyal üretilen hisseler için yfinance'den 5 dakikalık geçmişi indirir.
        BAN KORUMASI: 429 cooldown, 5dk aralik, max 25 oncelikli sembol.
        """
        now_ts = time.time()
        # 1. 429 Rate limit soguma kontrolu
        if now_ts < cls._rate_limit_until:
            wait_rem = int(cls._rate_limit_until - now_ts)
            print(f"[MarketData] Ban korumasi: Yahoo 429 bekleme modunda ({wait_rem} sn). Mevcut onbellek kullaniliyor.")
            return

        # 2. Cooldown kontrolu (en az 5 dakika / 300 saniye)
        if now_ts - cls._last_fetch_ts < 300:
            return

        conn = get_connection()
        cursor = conn.cursor()

        # BAN KORUMASI 3: 100+ hisse yerine SADECE acik pozisyonlar + ilk 15 aday
        cursor.execute("SELECT DISTINCT symbol FROM trades WHERE exit_time IS NULL")
        open_syms = [r["symbol"] for r in cursor.fetchall()]
        
        cursor.execute("SELECT symbol FROM signals WHERE date_str = ? ORDER BY score DESC LIMIT 15", (date_str,))
        cand_syms = [r["symbol"] for r in cursor.fetchall()]

        symbols = list(dict.fromkeys(open_syms + cand_syms))[:25]

        if not symbols:
            conn.close()
            return

        cls._last_fetch_ts = now_ts
        print(f"[MarketData] {date_str} için {len(symbols)} hissenin 5m verisi indiriliyor (period={period}, ban-guvenli)...")

        # Yahoo Finance bazen 5m vermeyebilir eski tarihler için, 1mo içinde verir.
        try:
            # interval = 5m; BUYUK tek istek (98 sembol) Yahoo'da ~30dk geriye
            # dusuk veri dondurdugu icin 10'lu parcalar halinde indiriliyor
            # (parcalar taze; tek istek ~2-3sn).
            insert_sql = """
                INSERT INTO market_data (date_str, timestamp, symbol, open, high, low, close, volume, interval, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, '5m', 'yfinance')
                ON CONFLICT(timestamp, symbol) DO NOTHING
            """
            all_rows = []
            chunk_size = 10
            for ci in range(0, len(symbols), chunk_size):
                chunk = symbols[ci:ci + chunk_size]
                try:
                    _pa_s = _get_pa_session()
                    data = yf.download(chunk, period=period, interval="5m", group_by='ticker', threads=False, progress=False, session=_pa_s) if _pa_s else yf.download(chunk, period=period, interval="5m", group_by='ticker', threads=True, progress=False)
                except Exception as _dl_err:
                    if "429" in str(_dl_err) or "Too Many Requests" in str(_dl_err):
                        cls._rate_limit_until = time.time() + 900
                        print(f"[MarketData] 429 tespit edildi, 15 dakika soguma moduna gecildi.")
                        break
                    continue
                time.sleep(1.5)  # Istekler arasi insani bekleme (ban korumasi)
                if data is None or data.empty:
                    continue
                for sym in chunk:
                    try:
                        if isinstance(data.columns, pd.MultiIndex):
                            if sym in data.columns.get_level_values(0):
                                df = data[sym]
                            else:
                                continue
                        else:
                            df = data
                    except Exception:
                        continue
                    df = df.dropna(how='all')
                    if df.empty:
                        continue

                    for idx_time, row in df.iterrows():
                        # Store and filter using the exchange's local timezone.
                        ts = pd.Timestamp(idx_time)
                        if ts.tzinfo is None:
                            ts = ts.tz_localize("Europe/Istanbul")
                        else:
                            ts = ts.tz_convert("Europe/Istanbul")
                        idx_date = ts.strftime("%Y-%m-%d")
                        if idx_date != date_str:
                            continue

                        _open = row['Open']
                        _high = row['High']
                        _low = row['Low']
                        _close = row['Close']
                        _vol = row['Volume']
                        values = [_open, _high, _low, _close, _vol]
                        if not all(pd.notna(v) and pd.api.types.is_number(v) for v in values):
                            continue
                        _open, _high, _low, _close, _vol = map(float, values)
                        if not all(map(lambda v: pd.notna(v) and abs(v) != float("inf"), values)):
                            continue
                        if min(_open, _high, _low, _close) <= 0 or _vol < 0:
                            continue
                        if _high < max(_open, _close, _low) or _low > min(_open, _close, _high):
                            continue
                        all_rows.append((date_str, ts.isoformat(), sym, _open, _high, _low, _close, _vol))

            # TEK executemany ile yaz (satir-satır INSERT uzak DB'de dakikalar aliyordu)
            if all_rows:
                try:
                    cursor.executemany(insert_sql, all_rows)
                except Exception as e:
                    print(f"[CRITICAL] MarketData executemany hatasi: {e}")
                    try:
                        from services.telegram_bot import send_telegram_message
                        send_telegram_message(f"🚨 SIMULASYON VERI YAZMA HATASI!\nMarket verileri (intraday) DB'ye yazilamadi!\nHata: {e}")
                    except:
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
    def get_market_data(date_str: str, symbol: str):
        """
        Backtester için yalnızca doğrulanmış 5 dakikalık veritabanı barlarını döndürür.
        Veri yoksa boş DataFrame döner; günlük veriyle ikame yapılmaz.
        """
        import pandas as pd
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT timestamp, open, high, low, close, volume
            FROM market_data
            WHERE date_str = ? AND symbol = ? AND interval = '5m'
            ORDER BY timestamp ASC
        """, (date_str, symbol))
        rows = cur.fetchall()
        conn.close()

        if rows:
            df = pd.DataFrame(
                [[r[1], r[2], r[3], r[4], r[5]] for r in rows],
                index=pd.to_datetime([r[0] for r in rows]),
                columns=['Open', 'High', 'Low', 'Close', 'Volume'],
            )
            df.index.name = 'Datetime'
            df.attrs.update({"source": "yfinance", "interval": "5m", "date": date_str})
            return df

        # Missing intraday data must remain missing. Never substitute a daily candle
        # into an intraday backtest: that would fabricate execution precision.
        empty = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        empty.attrs.update({"source": None, "interval": None, "data_status": "MISSING_INTRADAY"})
        return empty

