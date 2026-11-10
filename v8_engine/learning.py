import pandas as pd
import yfinance as yf
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid
import threading
import time
import json


def _get_pa_session():
    import requests, os
    if os.path.exists("/home/varantradarpro") or "pythonanywhere" in os.environ.get("PYTHONANYWHERE_DOMAIN", "").lower() or os.path.exists("/etc/pythonanywhere"):
        s = requests.Session()
        s.proxies = {"http": "http://proxy.server:3128", "https": "http://proxy.server:3128"}
        return s
    return None

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

        # Sunucu TZ'sinden bagimsiz olarak Istanbul naive zaman damgasi
        # (Render UTC calisir; bar index'leri Istanbul oldugu icin tutarli olmali)
        try:
            from zoneinfo import ZoneInfo
            _now = datetime.now(ZoneInfo("Europe/Istanbul")).replace(tzinfo=None)
        except Exception:
            _now = datetime.now()

        metrics = breakout_data.get("metrics", {}) or {}
        try:
            atr_val = metrics.get("atr_14")
            if atr_val is None or not pd.notna(atr_val) or float(atr_val) <= 0:
                atr_pct = float(metrics.get("atr_pct", 3.0) or 3.0)
                atr_val = float(entry_price) * atr_pct / 100.0
            atr_value = float(atr_val)
            if not pd.notna(atr_value) or atr_value <= 0 or not pd.notna(entry_price) or float(entry_price) <= 0:
                raise ValueError("valid ATR and entry price required")
            entry_price = float(entry_price)
        except (TypeError, ValueError):
            return None

        breakout_score = float(breakout_data.get("breakout_score", 0) or 0)
        fakeout_risk = float(breakout_data.get("fakeout_risk", 0) or 0)
        regime_code = str(regime or "UNKNOWN").upper()
        confidence_score = max(0.0, min(100.0, 0.60 * breakout_score + 0.40 * (100.0 - fakeout_risk)))
        if regime_code in {"BEAR", "STRONG_BEAR"}:
            confidence_score = max(0.0, confidence_score - (15.0 if regime_code == "BEAR" else 30.0))

        # Explicitly a rule-based quality index, never a statistical probability.
        features = {
            "breakout_score": breakout_data.get("breakout_score", 0),
            "fakeout_risk": breakout_data.get("fakeout_risk", 0),
            "rsi": breakout_data.get("metrics", {}).get("rsi", 50),
            "relative_volume": breakout_data.get("metrics", {}).get("relative_volume", 1),
            "atr_pct": breakout_data.get("metrics", {}).get("atr_pct", 0),
            "entry_status": execution_data.get("entry_status", "UNKNOWN"),
        }

        # ATR bazli dinamik stop/hedef: volatil hissede genis, sakin hissede sik.
        # Guvenli bantlar: stop %2-%8, hedef1 %2-%10, hedef2 %3-%15.
        atr_pct = 0.0
        try:
            atr_pct = float(breakout_data.get("metrics", {}).get("atr_pct", 0) or 0)
        except Exception:
            atr_pct = 0.0

        if atr_pct > 0:
            stop_dist_pct = max(2.0, min(8.0, atr_pct * 1.5))
            tgt1_dist_pct = max(2.0, min(10.0, atr_pct * 1.5))
            tgt2_dist_pct = max(3.0, min(15.0, atr_pct * 2.5))
        else:
            stop_dist_pct, tgt1_dist_pct, tgt2_dist_pct = 5.0, 3.0, 5.0

        signal_data = {
            "signal_id": signal_id,
            "symbol": symbol,
            "timestamp": _now.isoformat(),
            "strategy": "V8_BREAKOUT",
            "market_regime": regime,
            "score": breakout_data.get("breakout_score", 0),
            "entry_price": float(entry_price),
            "stop_price": float(entry_price * (1 - stop_dist_pct / 100.0)),
            "target1": float(entry_price * (1 + tgt1_dist_pct / 100.0)),
            "target2": float(entry_price * (1 + tgt2_dist_pct / 100.0)),
            "features_snapshot": features,
            "status": "ACTIVE",
            # KOHORT ETIKETI: yeni motor (V8 PRO: rejim kilidi + T+3 teyit +
            # A sinifi filtreler) ile uretilen kayit; istatistikler LEGACY
            # kayitlarindan ayri raporlanir.
            "engine_version": "V8_PRO"
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

    def update_active_outcomes(self, all_stats: dict = None) -> int:
        """Veritabanindaki sinyalleri tarar, all_symbols_stats ve intraday barlari
        kullanarak t3/t5/t10/t15/t30/t60/t120/t240/EOD fiyatlarini, MFE, MAE ve sonuclari backfill eder."""
        if not all_stats:
            try:
                import server
                g_cache = getattr(server, "GLOBAL_DASHBOARD_CACHE", None)
                if isinstance(g_cache, dict):
                    all_stats = g_cache.get("all_symbols_stats", {})
            except Exception:
                pass
        if not all_stats:
            try:
                import json
                with open("dashboard_cache.json", "r", encoding="utf-8") as f:
                    all_stats = json.load(f).get("all_symbols_stats", {})
            except Exception:
                pass

        if not all_stats:
            return 0

        from v8_engine.database import V8Database
        conn = V8Database.get_connection()
        cursor = conn.cursor()

        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo("Europe/Istanbul")).replace(tzinfo=None)
        except Exception:
            now = datetime.now()

        cursor.execute("""
            SELECT s.signal_id, s.symbol, s.timestamp, s.entry_price, s.status,
                   o.t_3m_price, o.t_5m_price, o.t_10m_price, o.t_15m_price,
                   o.t_30m_price, o.t_60m_price, o.t_120m_price, o.t_240m_price,
                   o.t_eod_price, o.max_favorable_excursion, o.max_adverse_excursion, o.final_result
            FROM v8_signals s
            LEFT JOIN v8_outcomes o ON s.signal_id = o.signal_id
            WHERE o.signal_id IS NULL 
               OR o.t_3m_price IS NULL 
               OR o.t_15m_price IS NULL 
               OR s.status = 'ACTIVE'
            ORDER BY s.timestamp DESC
            LIMIT 100
        """)
        rows = cursor.fetchall()
        updated_count = 0

        for r in rows:
            sig_id = r["signal_id"]
            sym = r["symbol"]
            ts_str = r["timestamp"]
            entry_price = float(r["entry_price"] or 0)
            if entry_price <= 0:
                continue

            try:
                sig_time = datetime.fromisoformat(ts_str)
                if sig_time.tzinfo is not None:
                    try:
                        from zoneinfo import ZoneInfo
                        sig_time = sig_time.astimezone(ZoneInfo("Europe/Istanbul")).replace(tzinfo=None)
                    except Exception:
                        sig_time = sig_time.replace(tzinfo=None)
            except Exception:
                continue

            elapsed_mins = (now - sig_time).total_seconds() / 60.0

            st = all_stats.get(sym) or all_stats.get(sym.replace(".IS", "")) or all_stats.get(sym + ".IS")
            if not st or not isinstance(st, dict):
                continue

            cur_p = float(st.get("Price") or st.get("Daily_Close") or entry_price)
            high_p = float(st.get("High") or cur_p)
            low_p = float(st.get("Low") or cur_p)

            bars = []
            hourly = (st.get("intraday_strength") or {}).get("hourly_profile") or []
            for h in hourly:
                try:
                    h_ts = pd.to_datetime(h.get("hour"))
                    if h_ts.tzinfo is not None:
                        try:
                            from zoneinfo import ZoneInfo
                            h_ts = h_ts.tz_convert("Europe/Istanbul").tz_localize(None)
                        except Exception:
                            h_ts = h_ts.tz_localize(None)
                    bars.append({"Date": h_ts, "Close": float(h.get("close", cur_p))})
                except Exception:
                    pass
            bars.append({"Date": now, "Close": cur_p})
            df = pd.DataFrame(bars).set_index("Date").sort_index() if bars else pd.DataFrame()

            def get_window_val(existing, mins):
                if existing is not None:
                    return existing
                if elapsed_mins < mins:
                    return None
                target_ts = sig_time + pd.Timedelta(minutes=mins)
                if not df.empty:
                    sub = df[df.index >= target_ts]
                    if not sub.empty:
                        return round(float(sub["Close"].iloc[0]), 2)
                return round(cur_p, 2)

            t3 = get_window_val(r["t_3m_price"], 3)
            t5 = get_window_val(r["t_5m_price"], 5)
            t10 = get_window_val(r["t_10m_price"], 10)
            t15 = get_window_val(r["t_15m_price"], 15)
            t30 = get_window_val(r["t_30m_price"], 30)
            t60 = get_window_val(r["t_60m_price"], 60)
            t120 = get_window_val(r["t_120m_price"], 120)
            t240 = get_window_val(r["t_240m_price"], 240)

            t_eod = r["t_eod_price"]
            signal_day_closed = (
                now.date() > sig_time.date()
                or (now.date() == sig_time.date() and (now.hour > 18 or (now.hour == 18 and now.minute >= 15)))
            )
            if t_eod is None and signal_day_closed:
                t_eod = round(float(st.get("Daily_Close") or cur_p), 2)

            mfe_calc = max(0.0, ((high_p - entry_price) / entry_price) * 100.0)
            mae_calc = min(0.0, ((low_p - entry_price) / entry_price) * 100.0)
            mfe = round(max(float(r["max_favorable_excursion"] or 0), mfe_calc), 2)
            mae = round(min(float(r["max_adverse_excursion"] or 0), mae_calc), 2)

            final_res = r["final_result"] or "PENDING"
            if mfe >= 3.0:
                final_res = "WIN"
            elif mae <= -2.0:
                final_res = "LOSS"
            elif signal_day_closed:
                final_res = "WIN" if cur_p > entry_price else "LOSS"

            cursor.execute("""
                INSERT INTO v8_outcomes (
                    signal_id, t_3m_price, t_5m_price, t_10m_price, t_15m_price,
                    t_30m_price, t_60m_price, t_120m_price, t_240m_price,
                    t_eod_price, t_eod_confirmed, t_1d_price,
                    max_favorable_excursion, max_adverse_excursion, final_result
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(signal_id) DO UPDATE SET
                    t_3m_price = COALESCE(excluded.t_3m_price, v8_outcomes.t_3m_price),
                    t_5m_price = COALESCE(excluded.t_5m_price, v8_outcomes.t_5m_price),
                    t_10m_price = COALESCE(excluded.t_10m_price, v8_outcomes.t_10m_price),
                    t_15m_price = COALESCE(excluded.t_15m_price, v8_outcomes.t_15m_price),
                    t_30m_price = COALESCE(excluded.t_30m_price, v8_outcomes.t_30m_price),
                    t_60m_price = COALESCE(excluded.t_60m_price, v8_outcomes.t_60m_price),
                    t_120m_price = COALESCE(excluded.t_120m_price, v8_outcomes.t_120m_price),
                    t_240m_price = COALESCE(excluded.t_240m_price, v8_outcomes.t_240m_price),
                    t_eod_price = COALESCE(excluded.t_eod_price, v8_outcomes.t_eod_price),
                    max_favorable_excursion = excluded.max_favorable_excursion,
                    max_adverse_excursion = excluded.max_adverse_excursion,
                    final_result = excluded.final_result
            """, (sig_id, t3, t5, t10, t15, t30, t60, t120, t240, t_eod, 1 if signal_day_closed else 0, None, mfe, mae, final_res))
            updated_count += 1

        conn.commit()
        conn.close()
        return updated_count

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
                    # (Istanbul simdi'sine gore kes; sunucu TZ'sinden bagimsiz)
                    try:
                        from zoneinfo import ZoneInfo
                        now = datetime.now(ZoneInfo("Europe/Istanbul")).replace(tzinfo=None)
                    except Exception:
                        now = datetime.now()
                    cutoff = (now - pd.Timedelta(days=7)).isoformat()
                    cursor.execute("SELECT * FROM v8_signals WHERE status='ACTIVE' AND timestamp >= ?", (cutoff,))
                    active_signals = cursor.fetchall()
                    
                    if not active_signals:
                        conn.close()
                        time.sleep(60)
                        continue
                        
                    # İlgili hisselerin anlik fiyatlarini cek
                    symbols = list(set([s['symbol'] for s in active_signals]))
                    _pa_s = _get_pa_session()
                    data = yf.download(symbols, period="5d", interval="1m", group_by='ticker', progress=False, session=_pa_s) if _pa_s else yf.download(symbols, period="5d", interval="1m", group_by='ticker', progress=False)

                    # 'now' zaten ustte Istanbul saatine gore ayarlandi (UTC ezmesin)
                    
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
                                        _pa_s = _get_pa_session()
                                        df = (yf.Ticker(sym, session=_pa_s) if _pa_s else yf.Ticker(sym)).history(period="5d", interval="1m").dropna(how='all').copy()
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

                            # EOD is immutable only after the signal day's session has closed.
                            signal_day_closed = (
                                now.date() > sig_time.date()
                                or (now.date() == sig_time.date() and (now.hour > 18 or (now.hour == 18 and now.minute >= 15)))
                            )
                            t_eod = _get_existing('t_eod_price')
                            t_eod_confirmed = bool(_get_existing('t_eod_confirmed') or 0)
                            if signal_day_closed and not t_eod_confirmed:
                                same_day = df[df.index.date == sig_time.date()]
                                if not same_day.empty:
                                    # Replace any legacy partial-day EOD value with the completed session close.
                                    t_eod = float(same_day['Close'].iloc[-1])

                            # T+1 means the next available trading session, not the next calendar day.
                            t_1d = _get_existing('t_1d_price')
                            next_trading_days = sorted({day for day in df.index.date if day > sig_time.date()})
                            if t_1d is None and next_trading_days:
                                next_day = next_trading_days[0]
                                next_day_closed = (
                                    now.date() > next_day
                                    or (now.date() == next_day and (now.hour > 18 or (now.hour == 18 and now.minute >= 15)))
                                )
                                if next_day_closed:
                                    next_bars = df[df.index.date == next_day]
                                    if not next_bars.empty:
                                        t_1d = float(next_bars['Close'].iloc[-1])

                            mfe = _get_existing('max_favorable_excursion') or 0.0
                            mae = _get_existing('max_adverse_excursion') or 0.0

                            # MFE/MAE: giris anindan sonraki barlarin high/low
                            # degerlerinden hesaplanir; kapanis fiyatlari ara tepe/dibi kaçırır.
                            try:
                                bars = df.loc[df.index >= sig_time]
                                if not bars.empty:
                                    highs = bars['High'] if 'High' in bars else bars['Close']
                                    lows = bars['Low'] if 'Low' in bars else bars['Close']
                                    high_pct = ((highs - entry_price) / entry_price) * 100.0
                                    low_pct = ((lows - entry_price) / entry_price) * 100.0
                                    mfe = max(float(high_pct.max()), 0.0)
                                    mae = min(float(low_pct.min()), 0.0)
                            except Exception:
                                pct_change = ((current_price - entry_price) / entry_price) * 100
                                mfe = max(mfe, pct_change, 0.0)
                                mae = min(mae, pct_change, 0.0)

                            status_update = "ACTIVE"
                            # Sinyal gun sonunda kapanir (seans bitisi ~18:15) ya da 6 saat
                            from datetime import time as _dtime
                            market_closed = now.time() >= _dtime(18, 15)
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
                                t_1d_price=COALESCE(v8_outcomes.t_1d_price, excluded.t_1d_price),
                                max_favorable_excursion=excluded.max_favorable_excursion,
                                max_adverse_excursion=excluded.max_adverse_excursion,
                                final_result=excluded.final_result
                            ''', (sig_id, t3, t5, t10, t15, t30, t60, t120, t240, t_eod, t_1d, mfe, mae, status_update))

                            if t_eod is not None and signal_day_closed and not t_eod_confirmed:
                                cursor.execute(
                                    "UPDATE v8_outcomes SET t_eod_price=?, t_eod_confirmed=1 WHERE signal_id=? AND COALESCE(t_eod_confirmed,0)=0",
                                    (float(t_eod), sig_id)
                                )

                            if status_update == "CLOSED":
                                # Final outcome uses the completed T+1 close, then EOD.
                                final_price = t_1d if t_1d is not None else t_eod
                                if final_price is None:
                                    final = "INSUFFICIENT_DATA"
                                else:
                                    net_pct = ((float(final_price) - entry_price) / entry_price) * 100
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


V8LearningEngine = OutcomeEngine
