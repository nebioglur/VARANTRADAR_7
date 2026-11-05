import os
import sys
import math
import json
import time
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Render (Linux) üzerinde saat dilimini Türkiye (UTC+3) yapmak için
if hasattr(time, 'tzset'):
    os.environ['TZ'] = 'Europe/Istanbul'
    time.tzset()

import numpy as np
import pandas as pd

import logging
from utils.sys_logger import log_error, log_info
import traceback

os.makedirs("data", exist_ok=True)
file_handler = logging.FileHandler("data/system_logs.txt", encoding="utf-8")
file_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', "%Y-%m-%d %H:%M:%S"))
logging.getLogger().addHandler(file_handler)
logging.getLogger().setLevel(logging.INFO)

from flask import Flask, request, jsonify, send_from_directory, make_response
try:
    from flask_cors import CORS
except ImportError:
    def CORS(app, *args, **kwargs):
        return app

try:
    import feedparser
except ImportError:
    feedparser = None

# Ana dizindeki main.py'deki fonksiyonu çağıracağız
from main import run_simulation_api
from decision.exceptions import InsufficientConfidenceError

# Scanner için gerekenler
from scanner.universal_scanner import UniversalScanner
from data.pipeline import DataPipeline
from data.providers.yfinance_provider import YFinanceProvider
from config.bist_symbols import BIST_SYMBOLS, BIST30_SYMBOLS, BIST50_SYMBOLS, YILDIZ_SYMBOLS, FX_SYMBOLS, COMMODITY_SYMBOLS, CRYPTO_SYMBOLS

def sanitize_for_json(obj):
    """
    Sözlük veya liste içindeki tüm NumPy tiplerini, NaN ve Sonsuz (Inf) değerlerini 
    JSON ile %100 uyumlu standart Python tiplerine (None / 0.0 vb.) çevirir.
    """
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, (float, np.floating)):
        if math.isnan(obj) or np.isnan(obj) or np.isinf(obj) or math.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, (int, np.integer)):
        return int(obj)
    elif isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return sanitize_for_json(obj.tolist())
    elif pd.isna(obj): # pd.NaT veya pandas NA
        return None
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    return obj

STATS_FILE = "stats.json"
GLOBAL_OPPORTUNITIES_CACHE = []

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Server] load_stats Error: {e}")
            return {"total_analyzed": 0}
    return {"total_analyzed": 0}

def save_stats(stats):
    try:
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f)
    except Exception as e:
        print(f"Stats save error: {e}")

CACHE_FILE = "dashboard_cache.json"
CACHE_MAX_AGE_MINUTES = 30  # Piyasa acikken cache bu sureden eski ise 'data_fresh=false'


def _cache_is_stale(data):
    """Cache'in ne kadar eski oldugunu kontrol eder."""
    from datetime import datetime
    if not isinstance(data, dict) or not data:
        return True, "cache bos"
    today_str = datetime.now().strftime("%Y-%m-%d")
    cache_date = data.get("cache_date")
    if cache_date != today_str:
        return True, f"onceki gunun cache'i ({cache_date})"
    ts = data.get("cache_timestamp")
    if ts:
        try:
            age_min = (datetime.now().timestamp() - float(ts)) / 60
            if age_min > CACHE_MAX_AGE_MINUTES:
                return True, f"cache {int(age_min)} dk eski"
            return False, f"cache {int(age_min)} dk oncesi"
        except Exception:
            pass
    return False, "yas bilinmiyor"


def _cache_age_hours(data):
    """Cache'in saat cinsinden yasi (cache_timestamp yoksa None)."""
    import time as _time
    ts = data.get("cache_timestamp") if isinstance(data, dict) else None
    if not ts:
        return None
    try:
        return (_time.time() - float(ts)) / 3600.0
    except Exception:
        return None


def load_dashboard_cache():
    import json, os
    from datetime import datetime

    def _accept(data, reason):
        """Bugunun cache'i her zaman kabul. Onceki gunun cache'i piyasa kapaliyken
        'Kapanis Verisi' olarak gosterilmek uzere son 72 saat icinde kabul edilir;
        boylece her yeniden baslatma sonrasi tablolar bos kalmaz."""
        if not isinstance(data, dict) or not data:
            return False
        stale, _ = _cache_is_stale(data)
        if not stale:
            return True
        age_h = _cache_age_hours(data)
        if age_h is not None and age_h <= 72:
            print(f"[CACHE] {reason}: son kapanis snapshot'i yuklenecek ({len(data.get('all_symbols_stats', {}))} hisse, yas {age_h:.1f} saat) - piyasa acilinca taze tarama gelir")
            return True
        print(f"[CACHE] {reason}: cok eski ({age_h if age_h is not None else 'bilinmiyor'} saat) - bos baslanacak")
        return False

    # Once DB'den (kalici veritabanindan) yuklemeyi dene
    try:
        from services.trade_database import get_connection
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM live_settings WHERE key = 'dashboard_cache'")
            row = cur.fetchone()
            if row and row["value"]:
                data = json.loads(row["value"])
                if _accept(data, "DB"):
                    print(f"[CACHE] DB'den yuklendi ({len(data.get('all_symbols_stats', {}))} hisse, tarih {data.get('cache_date')})")
                    return data
    except Exception as e:
        print(f"[CACHE] DB yukleme hatasi: {e}")

    # Eger DB bos ise (veya hata verdiyse), dosyadan yuklemeyi dene
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if _accept(data, "DOSYA"):
                    print(f"[CACHE] DOSYADAN yuklendi ({len(data.get('all_symbols_stats', {}))} hisse, tarih {data.get('cache_date')})")
                    return data
    except Exception:
        pass
    return {}

def sync_to_github():
    """Disabled: runtime must never commit or push live user data to main."""
    logging.warning("GitHub runtime sync is disabled; use an explicit, reviewed backup workflow.")
    return False


def save_dashboard_cache(data):
    import time, json
    try:
        data["cache_timestamp"] = time.time()
        clean = sanitize_for_json(data)
        json_str = json.dumps(clean, ensure_ascii=False)
        
        # 1. Veritabanina (kalici) kaydet
        try:
            from services.trade_database import get_connection, IS_PG
            placeholder = "%s" if IS_PG else "?"
            with get_connection() as conn:
                cur = conn.cursor()
                # Once kayit var mi kontrol et
                cur.execute("SELECT key FROM live_settings WHERE key = 'dashboard_cache'")
                exists = cur.fetchone()
                if exists:
                    cur.execute(f"UPDATE live_settings SET value = {placeholder} WHERE key = 'dashboard_cache'", (json_str,))
                else:
                    cur.execute(f"INSERT INTO live_settings (key, value) VALUES ('dashboard_cache', {placeholder})", (json_str,))
                conn.commit()
                print("[CACHE] Veritabanina basariyla kaydedildi.")
        except Exception as db_err:
            print(f"[CACHE] DB kayit hatasi: {db_err}")
            
        # 2. Dosyaya (gecici) kaydet
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(json_str)
    except Exception as e:
        print(f"Cache save error: {e}")

GLOBAL_DASHBOARD_CACHE = load_dashboard_cache()

def bist_market_status(now=None):
    """BIST seans durumunu Türkiye yerel saatine göre döndürür.

    Eski günlük cache verisi piyasa kapalıyken güncel fiyat gibi sunulmaz.
    Hafta sonu ve 10:00-18:10 dışındaki zamanlar kapalı kabul edilir.
    """
    now = now or datetime.now(ZoneInfo("Europe/Istanbul"))
    is_weekday = now.weekday() < 5
    open_at = now.replace(hour=10, minute=0, second=0, microsecond=0)
    close_at = now.replace(hour=18, minute=10, second=0, microsecond=0)
    is_open = is_weekday and open_at <= now <= close_at
    return {
        "is_open": is_open,
        "label": "AÇIK" if is_open else "KAPALI",
        "local_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "Europe/Istanbul",
        "next_session": "Hafta içi 10:00-18:10 (Türkiye saati)"
    }

def market_safe_dashboard_data(data, market_open):
    """Piyasa kapaliyken veriyi oldugu gibi gosterir."""
    safe = dict(data or {})
    return safe


# === VERITABANI TABLOLARINI OLUŞTUR (Simülasyon Motoru için) ===
try:
    from services.trade_database import init_db
    init_db()
    print("[SERVER] Simülasyon veritabanı tabloları hazır.")
except Exception as e_init:
    print(f"[SERVER] init_db hatası: {e_init}")

# === V8 MOTORU VERİTABANI VE TELEGRAM GÜVENCESİ ===
try:
    from v8_engine.database import V8Database
    V8Database.init_db()
    print("[SERVER] V8 motor veritabanı tabloları hazır.")
except Exception as e_v8_db:
    print(f"[SERVER] V8 init_db hatası: {e_v8_db}")

try:
    from services.telegram_bot import get_telegram_credentials, set_telegram_credentials, DEFAULT_BOT_TOKEN, DEFAULT_CHAT_ID
    _tok, _cid = get_telegram_credentials()
    if not _tok or not _cid:
        set_telegram_credentials(DEFAULT_BOT_TOKEN, DEFAULT_CHAT_ID)
except Exception as e_tg_init:
    print(f"[SERVER] Telegram kimlik güvencesi hatası: {e_tg_init}")

BACKGROUND_ERROR = "No Error"
def background_scanner():
    global BACKGROUND_ERROR
    try:
        _background_scanner_impl()
    except Exception as e:
        import traceback
        BACKGROUND_ERROR = str(e) + " - " + traceback.format_exc()

_live_collector_started = False
def start_live_data_collector():
    """Canli 5dk veri toplayici: agir ana taramadan BAGIMSIZ, seans saatlerinde
    her 5 dakikada bir market_data'yi tazeler. Boylece sinyal tablolari ve
    simulasyon guncel fiyatlarda calisir (30+ dk gecikme olmaz)."""
    global _live_collector_started
    if _live_collector_started:
        return
    _live_collector_started = True

    def _collector_loop():
        import time as _time
        from datetime import datetime as _dt
        from services.market_data import MarketDataManager
        while True:
            try:
                now = _dt.now(ZoneInfo("Europe/Istanbul"))
                weekday = now.weekday() < 5
                t = now.time()
                in_session = t >= _dt.strptime("09:50", "%H:%M").time() and t <= _dt.strptime("18:15", "%H:%M").time()

                # Zamanlanmis raporlar (seans disinda da calisir: sabah 09:30
                # bulteni seans oncesi, aksam 18:20 raporu seans sonrasi).
                if weekday:
                    try:
                        _v8_scheduled_reports(now)
                    except Exception:
                        pass

                if weekday and in_session:
                    d_str = now.strftime("%Y-%m-%d")
                    try:
                        MarketDataManager.fetch_and_store_intraday(d_str, period="5d")
                    except Exception as coll_err:
                        print(f"[LIVE DATA] toplama hatasi: {coll_err}")

                    # Telegram'a V8 aday listesi otomatik yollanmaz; kanal sadece
                    # seans açılışı, gerçek simülasyon AL/SAT olayları ve gün sonu özeti alır.

                        
                    # FAST PRICE UPDATE
                    try:
                        global GLOBAL_DASHBOARD_CACHE
                        if isinstance(GLOBAL_DASHBOARD_CACHE, dict) and "all_symbols_stats" in GLOBAL_DASHBOARD_CACHE:
                            print("[LIVE DATA] Hızlı fiyat güncellemesi başlatılıyor...")
                            import yfinance as _yf
                            from config.bist_symbols import BIST_SYMBOLS

                            syms_to_fetch = [s + ".IS" if not s.endswith(".IS") else s for s in BIST_SYMBOLS]
                            # Hızlı 1 günlük indirme
                            fast_data = _yf.download(syms_to_fetch, period="1d", interval="5m", threads=True, progress=False)
                            # Onceki gun resmi kapanisi (degisim capasi)
                            daily_data = _yf.download(syms_to_fetch, period="5d", interval="1d", threads=True, progress=False)

                            from datetime import datetime as _dt_cls
                            today_str = _dt_cls.now().strftime("%Y-%m-%d")
                            updates = 0
                            for sym in BIST_SYMBOLS:
                                sym_is = sym + ".IS" if not sym.endswith(".IS") else sym
                                if sym in GLOBAL_DASHBOARD_CACHE["all_symbols_stats"]:
                                    try:
                                        import math
                                        if len(syms_to_fetch) == 1:
                                            row = fast_data.iloc[-1]
                                        else:
                                            row = fast_data.xs(sym_is, level=1, axis=1).iloc[-1] if hasattr(fast_data.columns, 'levels') else fast_data[sym_is].iloc[-1]

                                        close_px = float(row["Close"])
                                        if not math.isnan(close_px) and close_px > 0:
                                            _stat_row = GLOBAL_DASHBOARD_CACHE["all_symbols_stats"][sym]
                                            _stat_row["Price"] = round(close_px, 2)
                                            _stat_row["Price_Stale"] = False
                                            _stat_row["Last_Price_Update"] = today_str
                                            # CAPA DOGRULAMA: tarayici cache'indeki Daily_Close
                                            # (onceki gun resmi kapanisi) ile Yahoo'nun onceki gun
                                            # kapanisi arasinda %25+ sapma varsa tarayici verisi
                                            # bayat demektir (orn. OZATD: cache 4650, gercek 140).
                                            # Bayat Daily_Close, Price ve degisim capasini da
                                            # beraberinde bozuyordu; taze kapanisla degistirilir.
                                            try:
                                                _cached_dc = float(_stat_row.get("Daily_Close") or 0)
                                                if _cached_dc > 0 and abs(_cached_dc - close_px) / _cached_dc > 0.25:
                                                    _stat_row["Daily_Close"] = round(close_px, 2)
                                                    _stat_row["Change_Pct"] = 0.0
                                            except Exception:
                                                pass
                                            # DEGISIM DOGRU CAPA: onceki gunun resmi kapanisina gore.
                                            # (Eski kod son 5dk mumun acilis-kapanis deltasi aliyordu
                                            #  -> cogu hisse 5dk'da yatay kaldigi icin 0.00 gorunuyordu.)
                                            try:
                                                if len(syms_to_fetch) == 1:
                                                    d_closes = daily_data["Close"].dropna()
                                                    d_dates = daily_data.index.strftime("%Y-%m-%d")
                                                else:
                                                    d_col = daily_data.xs(sym_is, level=1, axis=1) if hasattr(daily_data.columns, 'levels') else daily_data[sym_is]
                                                    d_closes = d_col["Close"].dropna()
                                                    d_dates = d_col.index.strftime("%Y-%m-%d")
                                                if len(d_closes) >= 2:
                                                    # Son gunluk satir bugun ise capasi bir onceki gun yap
                                                    if d_dates[-1] == today_str:
                                                        prev_close = float(d_closes.iloc[-2])
                                                    else:
                                                        prev_close = float(d_closes.iloc[-1])
                                                    # KENDI-KENDINE CAPA KORUMASI: prev anlik fiyata
                                                    # cok yakin ise bu bugunun yarim mumudur; boyle
                                                    # capa degisimi 0.00 uretir, kullanma.
                                                    if prev_close > 0 and abs(prev_close - close_px) / close_px > 0.0005:
                                                        GLOBAL_DASHBOARD_CACHE["all_symbols_stats"][sym]["Change_Pct"] = round(((close_px - prev_close) / prev_close) * 100, 2)
                                            except Exception:
                                                pass
                                            # YEDEK CAPA (Yahoo engelliyse): tarayici cache'indeki
                                            # Daily_Close (Is Yatirim = onceki gun resmi kapanisi)
                                            # ile degisim hesapla; bugunun yarim mumuna capa yapma.
                                            try:
                                                _stat_row = GLOBAL_DASHBOARD_CACHE["all_symbols_stats"][sym]
                                                if _stat_row.get("Change_Pct") in (0, 0.0, None):
                                                    _prev_stored = float(_stat_row.get("Daily_Close") or 0)
                                                    if _prev_stored > 0 and abs(_prev_stored - close_px) / close_px > 0.002:
                                                        _stat_row["Change_Pct"] = round(((close_px - _prev_stored) / _prev_stored) * 100, 2)
                                            except Exception:
                                                pass
                                            updates += 1
                                    except Exception:
                                        pass

                            # BAYATLIK ISARETLEME: bugun Yahoo'dan taze bar gelmeyen
                            # semboller (orn. cok dusuk likidite) eski fiyatiyla
                            # AL adayi listesine girmemeli; Price_Stale=True ile
                            # isaretlenir ve SUPER12/V8 filtreleri eler.
                            _stale_marked = 0
                            for _sym, _row in GLOBAL_DASHBOARD_CACHE["all_symbols_stats"].items():
                                if not isinstance(_row, dict):
                                    continue
                                if _row.get("Last_Price_Update") != today_str:
                                    _row["Price_Stale"] = True
                                    _stale_marked += 1

                            # CACHE GENELI YEDEK CAPA: Yahoo satiri gelmeyen semboller
                            # icin cache'teki Price ile Daily_Close (onceki gun resmi
                            # kapanisi) farkindan degisim uretilir. Yahoo tamamen
                            # engelliyse bile degisimler dolmus olur.
                            _fixed = 0
                            for _sym, _row in GLOBAL_DASHBOARD_CACHE["all_symbols_stats"].items():
                                if not isinstance(_row, dict):
                                    continue
                                if _row.get("Change_Pct") in (0, 0.0, None):
                                    try:
                                        _p = float(_row.get("Price") or 0)
                                        _c = float(_row.get("Daily_Close") or 0)
                                        if _p > 0 and _c > 0 and abs(_p - _c) / _c > 0.002:
                                            _row["Change_Pct"] = round(((_p - _c) / _c) * 100, 2)
                                            _fixed += 1
                                    except Exception:
                                        continue
                            if updates > 0 or _fixed > 0:
                                from datetime import datetime as _dt
                                GLOBAL_DASHBOARD_CACHE["cache_date"] = _dt.now().strftime("%Y-%m-%d")
                                save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
                                print(f"[LIVE DATA] {updates} hissenin canlı fiyatları Dashboard'a yansıtıldı! ({_fixed} sembol cache-ici yedek capa ile dolduruldu)")
                    except Exception as fast_err:
                        print(f"[LIVE DATA] Hızlı güncelleme hatası: {fast_err}")
            except Exception as e_outer:
                print(f"[LIVE DATA] dongu hatasi: {e_outer}")
            _time.sleep(5 * 60)

    t_live = threading.Thread(target=_collector_loop, daemon=True, name="live-data-collector")
    t_live.start()
    print("[LIVE DATA] Canli 5dk veri toplayici baslatildi (seans icinde her 5 dk).")

def _background_scanner_impl():
    import os
    

    # --- V8 ENGINE INIT ---
    try:
        from v8_engine.database import V8Database
        from v8_engine.regime import MarketRegimeEngine
        V8Database.init_db()
        regime_engine = MarketRegimeEngine()

        from v8_engine.learning import OutcomeEngine
        outcome_engine = OutcomeEngine()
        outcome_engine.run_outcome_tracker_loop()

    except Exception as e:
        print(f"[V8 INIT ERROR] {e}")
        regime_engine = None
    # ----------------------

    # --- CANLI İŞLEM TERMİNALİ (Akıllı TP/SL izleyici) ---
    try:
        from services.live_trade_monitor import run_monitor_loop
        run_monitor_loop(interval=45)
    except Exception as e:
        print(f"[LIVE MONITOR INIT ERROR] {e}")
    # ----------------------------------------------------

    """Arka planda çalışıp periyodik olarak TÜM BIST fırsatlarını tarar ve belleğe alır."""
    global GLOBAL_DASHBOARD_CACHE
    pipeline = DataPipeline()
    scanner = UniversalScanner(pipeline)
    
    from services.notification_manager import NotificationManager
    from datetime import datetime
    import time
    
    notif = NotificationManager()
    sent_tavan = {}
    sent_1h = {}
    sent_5m = {}
    
    # Sunucu yeniden başladı bildirimleri kapalı; açılış mesajı yalnızca seans saatinde gönderilir.

    
    def process_notifications(results):
        if not results or not isinstance(results, dict):
            return
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # 1. Tavan Adayları Bildirimleri (Aynı gün sadece 1 kez gönder)
        # KULLANICI İSTEĞİ: "Erken Kopuş" / "DAĞ" / kekliği / tavan radarı bildirimleri iptal
        for tavan in results.get("tavan_adaylari", []):
            sym = tavan.get("Symbol")
            if sym and sent_tavan.get(sym) != today_str:
                phase = str(tavan.get("Phase_Badge", ""))
                score = tavan.get("Score", 0)
                # Erken / DAĞ / kekliği / tavan radarı gibi spam bildirimler iptal
                skip_keywords = ["Erken", "DAĞ", "kek", "tavan radar", "Erken Kopuş"]
                if any(k.lower() in phase.lower() for k in skip_keywords):
                    print(f"[BACKGROUND] Telegram tavan bildirimi atlandi ({sym}): {phase}")
                    sent_tavan[sym] = today_str
                    continue
                notif.send_tavan_alert(sym, score, tavan.get("Report", ""), tavan.get("Position"), extra=tavan)
                sent_tavan[sym] = today_str
                time.sleep(0.5) # Telegram API rate limit önlemi
                
        # 2. 1 Saatlik Güçlü Fırsatlar Bildirimleri (Score 4 veya 5 olanlar, günde 1 kez)
        for opp in results.get("opportunities_1h", []):
            sym = opp.get("Symbol")
            score_5 = opp.get("Score_5", 0)
            if sym and score_5 >= 4 and sent_1h.get(sym) != today_str:
                notif.send_1h_opportunity_alert(opp)
                sent_1h[sym] = today_str
                time.sleep(0.5)
                
        # 3. 5m RSI Sinyalleri Bildirimleri (Aynı gün, aynı sinyali sadece 1 kez gönder)
        for rsi in results.get("signals_5m", []):
            sym = rsi.get("Symbol")
            sig = rsi.get("Signal")
            sig_key = f"{today_str}_{sig}"
            if sym and sent_5m.get(sym) != sig_key:
                notif.send_5m_rsi_alert(sym, sig, rsi.get("RSI", 0), rsi.get("Price", 0))
                sent_5m[sym] = sig_key
                time.sleep(0.5)
    
    # Hızlı Başlangıç (Fast Start): Eğer cache boşsa kullanıcıyı bekletmemek için sadece BIST 50'yi anında tara
    if not GLOBAL_DASHBOARD_CACHE:
        try:
            print("[BACKGROUND] Hızlı Başlangıç (Fast Start) - BIST 50 taranıyor...")
            fast_results = scanner.scan_pool_bulk(BIST50_SYMBOLS)
            from datetime import datetime
            fast_results["cache_date"] = datetime.now().strftime("%Y-%m-%d")

            _prev_regime = GLOBAL_DASHBOARD_CACHE.get("v8_market_regime") if isinstance(GLOBAL_DASHBOARD_CACHE, dict) else None
            GLOBAL_DASHBOARD_CACHE = sanitize_for_json(fast_results)
            if _prev_regime:
                GLOBAL_DASHBOARD_CACHE["v8_market_regime"] = _prev_regime
            save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
            print("[BACKGROUND] Hızlı Başlangıç Faz 1 tamamlandı - Günlük veriler HAZIR!")
            
            daily_stats = fast_results.get("all_symbols_stats", {})
            try:
                print("[BACKGROUND] Hızlı Başlangıç Faz 2 - 1 Saatlik (1h) Taraması yapılıyor...")
                fast_1h_res = scanner.scan_pool_bulk_1h(BIST50_SYMBOLS, daily_stats)
                GLOBAL_DASHBOARD_CACHE["opportunities_1h"] = sanitize_for_json(fast_1h_res.get("opportunities_1h", []))
                GLOBAL_DASHBOARD_CACHE["tavan_adaylari"] = sanitize_for_json(fast_1h_res.get("tavan_adaylari", []))
                GLOBAL_DASHBOARD_CACHE["stay_away_1h"] = sanitize_for_json(fast_1h_res.get("stay_away_1h", []))

                # V8 1h kirilim teyidini gunluk istatistiklere isle
                _v8_intra = sanitize_for_json(fast_1h_res.get("v8_intraday_breakout", {}))
                for _sym, _v8b in _v8_intra.items():
                    if _sym in daily_stats:
                        daily_stats[_sym]["v8_breakout_1h"] = _v8b
                save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
                
                # Hızlı Başlangıçta da sinyalleri DB'ye yaz (Simülasyon boş kalmasın)
                from services.market_data import MarketDataManager
                MarketDataManager.record_signals(fast_results["cache_date"], fast_1h_res.get("tavan_adaylari", []))
                MarketDataManager.fetch_and_store_intraday(fast_results["cache_date"])

                # Hızlı başlangıçta da bugunun tavan denetim kaydini olustur:
                # aksi halde her yeniden dagitimdan sonra istatistik eskse (son kayit eski tarih) kalir.
                try:
                    from services.tavan_tracker import TavanAuditTracker
                    bf_fast = TavanAuditTracker.backfill_from_db(fast_results["cache_date"])
                    if not bf_fast:
                        TavanAuditTracker.record_snapshot(fast_1h_res.get("tavan_adaylari", []), all_symbols_stats=daily_stats)
                    TavanAuditTracker.update_daily_progress(daily_stats)
                    print("[BACKGROUND] Hızlı Başlangıç tavan denetim kaydı oluşturuldu.")
                except Exception as e_audit:
                    print(f"[BACKGROUND] Hızlı Başlangıç denetim kaydı hatası: {e_audit}")
            except Exception as e_1h:
                print(f"[BACKGROUND] Hızlı Başlangıç 1h hatası: {e_1h}")
            
            try:
                print("[BACKGROUND] Hızlı Başlangıç Faz 3 - 5 Dakikalık (5m) Taraması yapılıyor...")
                valid_bist50 = [s for s in BIST50_SYMBOLS if s in daily_stats]
                fast_5m = scanner.scan_pool_bulk_5m(valid_bist50)
                GLOBAL_DASHBOARD_CACHE["signals_5m"] = sanitize_for_json(fast_5m)
                save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
            except Exception as e_5m:
                print(f"[BACKGROUND] Hızlı Başlangıç 5m hatası: {e_5m}")
            
            # Otomatik tarayıcı aday bildirimleri kapalı; istenen Telegram akışı yalnızca simülasyondur.

        except Exception as e:
            print(f"[BACKGROUND] Hızlı Başlangıç Hatası: {e}")
            import traceback
            traceback.print_exc()

    while True:
        try:
            
            # --- V8 REGIME UPDATE ---
            if regime_engine:
                try:
                    regime_data = regime_engine.determine_regime()
                    GLOBAL_DASHBOARD_CACHE["v8_market_regime"] = regime_data
                    print(f"[V8 REGIME] Current Market Regime: {regime_data.get('regime')} (Score: {regime_data.get('score')})")
                except Exception as re_e:
                    print(f"[V8 REGIME ERROR] {re_e}")
            # ------------------------
            
            print("[BACKGROUND] Tüm BIST hisseleri için Kapsamlı (Bulk) Günlük Data indiriliyor...")
            
            # 550 hisseyi tek bir pakette indir:
            results = scanner.scan_pool_bulk(BIST_SYMBOLS)
            from datetime import datetime
            if isinstance(results, dict): results["cache_date"] = datetime.now().strftime("%Y-%m-%d")
            
            from datetime import datetime
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            stats_count = len(results.get("all_symbols_stats", {})) if isinstance(results, dict) else 0
            
            if results and isinstance(results, dict) and stats_count > 50:
                # Mevcut 1h, tavan ve 5m verilerini KORU!
                if "opportunities_1h" in GLOBAL_DASHBOARD_CACHE:
                    results["opportunities_1h"] = GLOBAL_DASHBOARD_CACHE["opportunities_1h"]
                if "tavan_adaylari" in GLOBAL_DASHBOARD_CACHE:
                    results["tavan_adaylari"] = GLOBAL_DASHBOARD_CACHE["tavan_adaylari"]
                if "stay_away_1h" in GLOBAL_DASHBOARD_CACHE:
                    results["stay_away_1h"] = GLOBAL_DASHBOARD_CACHE["stay_away_1h"]
                if "signals_5m" in GLOBAL_DASHBOARD_CACHE:
                    results["signals_5m"] = GLOBAL_DASHBOARD_CACHE["signals_5m"]
                if "v8_market_regime" in GLOBAL_DASHBOARD_CACHE:
                    results["v8_market_regime"] = GLOBAL_DASHBOARD_CACHE["v8_market_regime"]

                # Sembol istatistikleri TAM DEGISTIRILMEZ, onceki veriyle BIRLESTIRILIR:
                # kismi taramalar onceki kapsamayi silmesin (606 -> 48 gibi kuculmeler olmasin).
                _prev_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {}) if isinstance(GLOBAL_DASHBOARD_CACHE, dict) else {}
                if not isinstance(_prev_stats, dict):
                    _prev_stats = {}
                _merged_stats = dict(_prev_stats)
                _merged_stats.update(sanitize_for_json(results.get("all_symbols_stats", {})))
                results["all_symbols_stats"] = _merged_stats

                GLOBAL_DASHBOARD_CACHE = sanitize_for_json(results)
                save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
                print(f"[BACKGROUND] Günlük veriler güncellendi ({stats_count} yeni, toplam {len(_merged_stats)} hisse). 1h taraması başlıyor...")
            elif results and isinstance(results, dict) and stats_count > 0:
                # Kısmi veri geldi: Sembol istatistiklerini mevcut cache ile birleştir,
                # kapsama alanı sonraki döngülerde kademeli olarak büyüsün.
                if not isinstance(GLOBAL_DASHBOARD_CACHE, dict):
                    GLOBAL_DASHBOARD_CACHE = {}
                existing_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
                if not isinstance(existing_stats, dict):
                    existing_stats = {}
                existing_stats.update(sanitize_for_json(results.get("all_symbols_stats", {})))
                GLOBAL_DASHBOARD_CACHE["all_symbols_stats"] = existing_stats
                GLOBAL_DASHBOARD_CACHE["cache_date"] = today_str
                save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
                print(f"[BACKGROUND] Kısmi veri geldi ({stats_count} hisse). Mevcut cache ile birleştirildi (toplam {len(existing_stats)} hisse).")
                results = GLOBAL_DASHBOARD_CACHE
            else:
                print(f"[BACKGROUND] Yfinance hatası veya boş veri! results length: {len(results.get('all_symbols_stats', {})) if isinstance(results, dict) else 0}. Cache korunuyor.")
                # Eger cache hic yoksa, en azindan bos listelerle dolsun ki UI patlamasin.
                if not GLOBAL_DASHBOARD_CACHE:
                    if isinstance(results, dict) and "v8_market_regime" not in results:
                        try:
                            results["v8_market_regime"] = regime_engine.determine_regime() if regime_engine else {"regime": "NEUTRAL", "score": 50.0, "xu100_trend": 0.0}
                        except Exception:
                            pass
                    GLOBAL_DASHBOARD_CACHE = results
                results = GLOBAL_DASHBOARD_CACHE
                
            if results and isinstance(results, dict):
                daily_stats = results.get("all_symbols_stats", {})
                try:
                    res_1h = scanner.scan_pool_bulk_1h(BIST_SYMBOLS, daily_stats)
                    if res_1h and isinstance(res_1h, dict):
                        tavan_candidates = res_1h.get("tavan_adaylari", [])
                        # Gün içi güç metriklerini mevcut all_symbols_stats'a entegre et
                        intra_stats = res_1h.get("all_symbols_stats", {})
                        existing_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
                        for sym, stats in intra_stats.items():
                            if sym in existing_stats:
                                existing_stats[sym]["intraday_strength"] = stats.get("intraday_strength")
                            else:
                                existing_stats[sym] = stats
                        # V8 1h kirilim teyidini gunluk istatistiklere isle
                        _v8_intra = sanitize_for_json(res_1h.get("v8_intraday_breakout", {}))
                        for _sym, _v8b in _v8_intra.items():
                            if _sym in existing_stats:
                                existing_stats[_sym]["v8_breakout_1h"] = _v8b
                        GLOBAL_DASHBOARD_CACHE["all_symbols_stats"] = existing_stats
                        GLOBAL_DASHBOARD_CACHE["opportunities_1h"] = sanitize_for_json(res_1h.get("opportunities_1h", []))
                        GLOBAL_DASHBOARD_CACHE["tavan_adaylari"] = sanitize_for_json(tavan_candidates)
                        GLOBAL_DASHBOARD_CACHE["stay_away_1h"] = sanitize_for_json(res_1h.get("stay_away_1h", []))
                        save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
                        
                        # Belirli Saatlerdeki Tavan Listesi Bellek Kaydı & 18:10 Kapanış Denetimi
                        try:
                            from services.tavan_tracker import TavanAuditTracker
                            TavanAuditTracker.record_snapshot(tavan_candidates, all_symbols_stats=daily_stats)
                            TavanAuditTracker.update_daily_progress(daily_stats)
                            
                            # YENİ MİMARİ: SQLite'a sinyalleri ve market datasını kaydet
                            from services.market_data import MarketDataManager
                            from services.simulation_engine import SimulationEngine
                            from datetime import datetime
                            d_str = datetime.now().strftime("%Y-%m-%d")
                            MarketDataManager.record_signals(d_str, tavan_candidates)
                            MarketDataManager.fetch_and_store_intraday(d_str)
                            
                            # Günlük simülasyon tek koşturucuda çalışır: simulation_loop (her 2 dk).
                            # Buradan ikinci kez çağrılırsa iki replay aynı anda çalışır; bu,
                            # mükerrer Telegram mesajlarına ve aynı hissenin eşzamanlı
                            # AL/SAT görünmesine neden oluyordu. (Koşturucu: simulation_loop / manuel API)

                            
                        except Exception as e_audit:
                            print(f"[BACKGROUND] Yeni Motor Hatası: {e_audit}")
                            import traceback
                            traceback.print_exc()
                        
                        # Runtime GitHub writes are intentionally disabled.
                            
                        print("[BACKGROUND] 1h ve Tavan taraması tamamlandı, saatlik tavan denetçisine kaydedildi.")
                except Exception as e_1h:
                    print(f"[BACKGROUND] 1h Tarama hatası: {e_1h}")
                
                # Otomatik tavan/RSI/saatlik fırsat Telegram mesajları kapalı.
                print(f"[BACKGROUND] Kapsamlı Tarama tamamlandı. Veriler önbelleğe ve diske kaydedildi.")
            
        except Exception as e:
            print(f"[BACKGROUND] Bulk Tarama hatası: {e}")
            import traceback
            traceback.print_exc()
            

        # --- MTF BACKGROUND SCAN ---
        try:
            print("[BACKGROUND] MTF (1h+15m) taramasi basladi...")
            from services.mtf_scanner import MTFScanner
            from config.bist_symbols import YILDIZ_SYMBOLS
            mtf_results = MTFScanner.scan_pool(YILDIZ_SYMBOLS, max_symbols=200)
            GLOBAL_DASHBOARD_CACHE["mtf_results"] = sanitize_for_json(mtf_results)
            save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
            print(f"[BACKGROUND] MTF tamamlandi: {len(mtf_results)} hisse bulundu.")
        except Exception as e_mtf:
            print(f"[BACKGROUND] MTF Hatasi: {e_mtf}")

        # Dinlen (15 dakika)
        # Kullanici ozel kural: 10:00'da kesin, 17:58'de kesin, arada 10 dk aralikla
        def get_next_run_seconds():
            import datetime
            from zoneinfo import ZoneInfo
            now = datetime.datetime.now(ZoneInfo("Europe/Istanbul"))
            t_10 = now.replace(hour=10, minute=0, second=0, microsecond=0)
            t_1810 = now.replace(hour=18, minute=10, second=0, microsecond=0)
            
            # Piyasa saatleri icinde (10:00 - 18:10) her 10 dakika
            if t_10 <= now <= t_1810:
                return 600.0
            
            # Piyasa disinda her saat (test/gece gelistirme icin)
            return 3600.0
            
        sleep_secs = get_next_run_seconds()
        print(f"[BACKGROUND] Siradaki tarama icin {int(sleep_secs)} saniye bekleniyor...")
        time.sleep(sleep_secs)


def simulation_loop():
    """SIMULASYON SUREKLI ARKA PLAN DONGUSU:
    - Her 2 dakikada bir calisir (piyasa acik/kapali fark etmez).
    - Piyasa saatlerinde (10:00 - 18:10) gercek guncel barlari alir.
    - Piyasa disinda son eldeki verilerle simulasyonu oynatmaya devam eder,
      boylece test/arka-plan bildirimleri kesintisiz gider.
    - Her AL/SAT islemi aninda Telegram bildirimi gider."""
    while True:
        sleep_secs = 120.0
        try:
            now = datetime.now(ZoneInfo("Europe/Istanbul"))
            d_str = now.strftime("%Y-%m-%d")
            t_open = now.replace(hour=10, minute=0, second=0, microsecond=0)
            t_close = now.replace(hour=18, minute=10, second=0, microsecond=0)
            in_market = t_open <= now <= t_close

            if in_market:
                try:
                    from services.market_data import MarketDataManager
                    MarketDataManager.fetch_and_store_intraday(d_str, period="5d")
                except Exception as _md_err:
                    print(f"[SIMLOOP] Intraday veri hatasi: {_md_err}")

            try:
                from services.trade_database import get_connection as _get_conn
                with _get_conn() as _uc:
                    _cur = _uc.cursor()
                    _cur.execute("SELECT owner_key FROM app_users")
                    _owners = [r["owner_key"] for r in _cur.fetchall()]
            except Exception:
                _owners = []
            if not _owners:
                _owners = ["local:nebioglur"]
            if "local:nebioglur" not in _owners:
                _owners.append("local:nebioglur")

            for _owner in _owners:
                try:
                    from services.simulation_engine import SimulationEngine
                    SimulationEngine(owner=_owner).run_daily_simulation(d_str)
                except Exception as _sim_err:
                    print(f"[SIMLOOP] Sim hatasi ({_owner}): {_sim_err}")

        except Exception as e:
            print(f"[SIMLOOP] Hata: {e}")
            sleep_secs = 300.0
        time.sleep(sleep_secs)

# Varant Sembolleri (Örnek Liste - IS Warrant yapısı)
# ⚠️ DİKKAT: Bu varant sembolleri eski vadeli (Temmuz 2024). Güncel vadeli sembollerle değiştirilmelidir.
import warnings
warnings.warn("WARRANT_SYMBOLS listesi eski vadeli semboller içeriyor (240726). Lütfen güncelleyin.", stacklevel=2)
WARRANT_SYMBOLS = [
    "GARAN-240726-C-130.IS", "GARAN-240726-P-120.IS",
    "THYAO-240726-C-350.IS", "THYAO-240726-P-300.IS",
    "ASELS-240726-C-80.IS", "ASELS-240726-P-60.IS",
    "TUPRS-240726-C-200.IS", "TUPRS-240726-P-150.IS",
    "AKBNK-240726-C-60.IS", "AKBNK-240726-P-50.IS",
    "EREGL-240726-C-60.IS", "EREGL-240726-P-45.IS",
    "SAHOL-240726-C-90.IS", "SAHOL-240726-P-75.IS",
    "BIMAS-240726-C-600.IS", "BIMAS-240726-P-500.IS",
    "KCHOL-240726-C-250.IS", "KCHOL-240726-P-200.IS",
    "SISE-240726-C-100.IS", "SISE-240726-P-80.IS",
]

# Tüm sembol listesi (autocomplete için)
ALL_SYMBOLS = [s.replace('.IS','') for s in BIST_SYMBOLS] + [w.replace('.IS','') for w in WARRANT_SYMBOLS] + FX_SYMBOLS + COMMODITY_SYMBOLS + CRYPTO_SYMBOLS
from analysis.technical import TechnicalEngine

app = Flask(__name__, static_folder='ui', static_url_path='')

import gzip
import io
from flask import request



# Same-origin by default; cross-origin access requires an explicit allow-list.
_allowed_origins = [x.strip() for x in os.environ.get("CORS_ORIGINS", "").split(",") if x.strip()]
CORS(app, origins=_allowed_origins, supports_credentials=True)

# ============ SESSION AUTH (GÜVENLİK) ============
import os
from flask import request, Response, session, redirect, jsonify, render_template_string

import secrets
_configured_secret = os.environ.get("SECRET_KEY", "varantradar_secret_key_2026_prod_secure")
_is_production = (os.environ.get("ENVIRONMENT", "").lower() == "production" or os.environ.get("RENDER") == "true")
app.secret_key = _configured_secret or secrets.token_urlsafe(48)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=(os.environ.get("ENVIRONMENT", "").lower() == "production" or os.environ.get("RENDER") == "true"))

# --- Verdent-Managed Supabase Auth (public browser config) ---
# AUTH KAYNAGI (Verdent-managed Supabase Auth) — bilinçli olarak env override KULLANMAZ:
# Render ortaminda eski proje env'leri kaldiysa bile giris her zaman AKTIF projeyle calisir.
# (Eski proje JWT anahtarlari gecersizlesti -> "invalid JWT signature" hatasinin kökü.)
AUTH_SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://kfslwkmrnjqxirzhfmbn.supabase.co")
SUPABASE_PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_RP_ouZJiDHK_PA_3o1dmfg_G5BgAuzl")
SUPABASE_URL = AUTH_SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY = SUPABASE_PUBLISHABLE_KEY

_jwks_client = None

def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        import jwt
        _jwks_client = jwt.PyJWKClient(
            f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json",
            cache_keys=True,
            lifespan=3600
        )
    return _jwks_client

_user_token_cache = {}

def _decode_jwt_unverified(token: str):
    """JWT payload'ini imzayi dogrulamadan okur (yalnizca ISS/ref teshisi icin)."""
    try:
        import base64
        p = token.split('.')[1]
        p += '=' * (-len(p) % 4)
        return json.loads(base64.urlsafe_b64decode(p.encode()).decode('utf-8', 'ignore'))
    except Exception:
        return None

def _supabase_user_from_endpoint(base_url: str, token: str, apikey):
    import urllib.request
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    if apikey:
        headers["apikey"] = apikey
    req = urllib.request.Request(
        f"{base_url}/auth/v1/user",
        headers=headers,
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))

def verify_supabase_token(token: str):
    """Validate a Supabase token only against explicitly configured HTTPS endpoints.

    JWT claims are untrusted until verified and must never be used to construct
    an outbound URL (prevents issuer-controlled SSRF).
    """
    import hashlib
    import time as _time
    import urllib.error

    if not isinstance(token, str) or len(token) > 8192 or token.count(".") != 2:
        return None, "invalid token format"

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = _time.time()
    cached = _user_token_cache.get(token_hash)
    if cached and cached[1] > now:
        return cached[0], None

    unverified = _decode_jwt_unverified(token)
    iss = (unverified or {}).get("iss") or ""
    configured = [SUPABASE_URL] + [
        value.strip() for value in os.environ.get("SUPABASE_AUTH_URLS", "").split(",")
        if value.strip()
    ]
    allowed = []
    for base in configured:
        base = base.rstrip("/")
        if base.startswith("https://") and base not in allowed:
            allowed.append(base)

    # The issuer must match an operator-configured endpoint exactly.
    matching = [
        base for base in allowed
        if iss in (base + "/auth/v1", base + "/auth/v1/")
    ]
    if not matching:
        return None, "untrusted token issuer"

    last_error = "verification failed"
    for base in matching:
        for key_try in (SUPABASE_PUBLISHABLE_KEY, None):
            try:
                user = _supabase_user_from_endpoint(base, token, key_try)
                user_id = user.get("id") or user.get("sub")
                if user_id and (not unverified or not unverified.get("sub") or user_id == unverified.get("sub")):
                    _user_token_cache[token_hash] = (user_id, now + 120)
                    return user_id, None
            except urllib.error.HTTPError as exc:
                last_error = "provider rejected token"
                continue
            except Exception:
                last_error = "provider verification unavailable"
                break
    return None, last_error

def _migrate_legacy_owner_data(new_owner: str, email: str):
    """Ayni e-postayla eski Supabase projesinde acilan (sb:...) hesaplarin
    simulasyon/portfoy verisini yeni oturum sahibine tasir (yeni hesaba veri
    yoksa, eski hesapta varsa). Auth projesi degisiminde veri kaybini onler."""
    if not email:
        return
    try:
        from services.trade_database import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT owner_key FROM app_users WHERE email=? AND owner_key<>? AND owner_key LIKE 'sb:%'",
                  (email, new_owner))
        legacy = [(r[0] if not hasattr(r, 'keys') else r['owner_key']) for r in c.fetchall()]
        if not legacy:
            conn.close()
            return
        for lg in legacy:
            for table in ('trades', 'equity_log', 'live_positions'):
                try:
                    c.execute(f"SELECT COUNT(*) FROM {table} WHERE owner=?", (new_owner,))
                    has_new = (c.fetchone()[0] or 0) > 0
                    c.execute(f"SELECT COUNT(*) FROM {table} WHERE owner=?", (lg,))
                    has_legacy = (c.fetchone()[0] or 0) > 0
                    if has_legacy and not has_new:
                        c.execute(f"UPDATE {table} SET owner=? WHERE owner=?", (new_owner, lg))
                        print(f"[AUTH] Veri gocu: {table} {lg} -> {new_owner}")
                except Exception as _t_err:
                    continue
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[AUTH] Veri gocu hatasi: {e}")

@app.route('/api/auth_config', methods=['GET'])
def api_auth_config():
    """Tarayici icin genel (public) auth yapilandirmasi."""
    return jsonify({
        "status": "success",
        "supabase_url": SUPABASE_URL,
        "publishable_key": SUPABASE_PUBLISHABLE_KEY,
        "oauth_initiate_url": "https://cloud-oauth.verdent.ai/app/initiate",
        "locale": "tr"
    })

@app.route('/api/client_log', methods=['POST'])
def api_client_log():
    """Tarayici tarafindan gelen auth/istisna bildirimlerini sistem gunlugune yazar."""
    try:
        data = request.get_json(silent=True) or {}
        msg = str(data.get('m') or '').replace('\n', ' ')[:500]
        if msg:
            with open('data/system_logs.txt', 'a', encoding='utf-8') as f:
                stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{stamp}] [CLIENT] {msg}\n")
    except Exception:
        pass
    return jsonify({"status": "ok"})


@app.route('/robots.txt')
def robots_txt():
    host = request.headers.get('X-Forwarded-Host', request.host)
    scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
    base = f"{scheme}://{host}"
    body = ("User-agent: *\n"
            "Allow: /\n"
            "Disallow: /api/\n\n"
            f"Sitemap: {base}/sitemap.xml\n")
    resp = make_response(body)
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


@app.route('/sitemap.xml')
def sitemap_xml():
    host = request.headers.get('X-Forwarded-Host', request.host)
    scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
    base = f"{scheme}://{host}"
    body = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f'  <url><loc>{base}/</loc>'
            '<changefreq>daily</changefreq><priority>1.0</priority></url>\n'
            '</urlset>\n')
    resp = make_response(body)
    resp.headers["Content-Type"] = "application/xml; charset=utf-8"
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp


# ========== HESAP BAZLI PORTFOY (OWNER) YONETIMI ==========
def get_owner_key():
    """Oturum sahibinin portfoy anahtarini dondurur:
    Supabase -> sb:<user_id>, klasik giris -> local:<username>."""
    uid = session.get('supabase_user_id')
    if uid:
        return f"sb:{uid}"
    uname = session.get('username')
    if uname:
        return f"local:{uname}"
    return "local:nebioglur"


def is_admin_owner(owner=None):
    return (owner or get_owner_key()) == os.environ.get('ADMIN_OWNER', 'local:nebioglur')


def upsert_app_user(owner_key, email=None, display_name=None):
    """Giris yapan hesabi app_users tablosuna kaydeder/gunceller."""
    try:
        from services.trade_database import get_connection
        now = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M:%S")
        conn = get_connection()
        c = conn.cursor()
        c.execute("""INSERT INTO app_users (owner_key, email, display_name, created_at, last_login)
                     VALUES (?, ?, ?, ?, ?)
                     ON CONFLICT(owner_key) DO UPDATE SET
                         email=COALESCE(excluded.email, app_users.email),
                         display_name=COALESCE(excluded.display_name, app_users.display_name),
                         last_login=excluded.last_login""",
                  (owner_key, email, display_name, now, now))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[AUTH] app_users upsert hatasi: {e}")


@app.route('/api/auth/session', methods=['POST'])
def api_auth_session():
    def log_auth(m):
        try:
            with open('data/system_logs.txt', 'a', encoding='utf-8') as f:
                import datetime
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [AUTH-DEBUG] {m}\n")
        except: pass
        print("[AUTH-DEBUG]", m)

    log_auth("api_auth_session basladi")
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        log_auth("Missing bearer token")
        return jsonify({"status": "error", "message": "Missing bearer token"}), 401
    token = auth_header[7:].strip()
    log_auth("Bearer token received")
    user_id, err_msg = verify_supabase_token(token)
    if not user_id:
        log_auth("Bearer token verification failed")
        return jsonify({"status": "error", "message": "Token doğrulanamadı"}), 401
    log_auth("Bearer token verified")
    # E-postayi JWT payload'indan oku (token zaten dogrulandi)
    email = None
    try:
        import base64
        payload_b64 = token.split('.')[1]
        payload_b64 += '=' * (-len(payload_b64) % 4)
        email = json.loads(base64.urlsafe_b64decode(payload_b64)).get('email')
    except Exception:
        pass
    owner = f"sb:{user_id}"
    upsert_app_user(owner, email=email, display_name=email)
    # Auth projesi degisimi sonrasi ayni e-postanin eski hesap verisini tasimal
    try:
        _migrate_legacy_owner_data(owner, email)
    except Exception as _mig_err:
        print(f"[AUTH] Goc cagri hatasi: {_mig_err}")
    session['logged_in'] = True
    session['supabase_user_id'] = user_id
    return jsonify({"status": "success", "user_id": user_id})

@app.before_request
def require_auth():
    if request.method == 'OPTIONS': return
    
    allowed = ['/login', '/logout', '/api/ping', '/api/auth_config', '/api/auth/session', '/api/system/git_pull', '/api/system/deploy']
    if request.path in allowed: return
    
    # Allow static assets for login page
    if request.path.endswith('.css') or request.path.endswith('.js') or request.path.endswith('.png') or request.path.endswith('.woff2'):
        return

    # Arama motorlari + PWA dosyalari + APK indirme oturum kapisi disinda
    if request.path in ('/robots.txt', '/sitemap.xml', '/manifest.json', '/sw.js', '/icons/icon-192.png', '/icons/icon-512.png'):
        return
    if request.path == '/apk/VarantRadarPro.apk':
        return

    if not session.get('logged_in'):
        # Dogrudan Bearer token ile gelen API istekleri (script/araclar icin)
        auth_header = request.headers.get('Authorization', '')
        if request.path.startswith('/api/') and auth_header.startswith('Bearer '):
            _uid, _uerr = verify_supabase_token(auth_header[7:].strip())
            if _uid:
                session['logged_in'] = True
                session['supabase_user_id'] = _uid
                return
        if request.path.startswith('/api/'):
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        return redirect('/login')

def _base_url():
    """Gelen istege gore canonical base URL uretir (proxy'den gelen hostu korur)."""
    host = request.headers.get('X-Forwarded-Host', request.host)
    scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
    # Verdent/Render proxy'de http gelirse disariya https olarak cikar
    if scheme == 'http' and not host.startswith('localhost'):
        scheme = 'https'
    return f"{scheme}://{host}"


@app.route('/login', methods=['GET'])
def login():
    # Giris artık tarayici tarafinda Verdent-managed Supabase Auth ile yapilir
    # (@verdent/auth-js builtin UI). Sunucu tarafinda form login yoktur.
    # CLASSIC_ONLY=1 ise (bagimsiz yedek site) sadece klasik kullanici/sifre formu gosterilir.
    try:
        with open('ui/login.html', 'r', encoding='utf-8') as f:
            html = f.read()
        html = html.replace('{{BASE_URL}}', _base_url())
        if os.environ.get('CLASSIC_ONLY') == '1':
            flag = '<script>window.VR_CLASSIC_ONLY=1;</script>'
            if '<head>' in html:
                html = html.replace('<head>', '<head>' + flag, 1)
        # Login HTML'i tarayici cache'ine takilirsa eski auth kodu calismaya
        # devam eder (Render'da "invalid JWT" donucusunun sebeplerinden biri).
        resp = make_response(html)
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    except:
        return "login.html bulunamadi", 404

@app.route('/login', methods=['POST'])
def login_post():
    """Klasik kullanici adi / sifre girisi (yedek giris yolu).

    ADMIN_USER / ADMIN_PASS ortam degiskenleriyle override edilebilir.
    """
    data = request.get_json(silent=True) or request.form
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    # Çok kullanıcılı klasik giriş: her kullanıcı kendi owner anahtarıyla (local:<ad>)
    # ayrı hesaba sahip olur. Ortam değişkenleriyle override edilebilir.
    valid_users = {
        os.environ.get('ADMIN_USER', 'nebioglur'): os.environ.get('ADMIN_PASS', '123'),
        os.environ.get('SARI_USER', 'sari'): os.environ.get('SARI_PASS', '123'),
    }
    if username in valid_users and password == valid_users[username]:
        session['logged_in'] = True
        session['username'] = username
        upsert_app_user(f"local:{username}", display_name=username)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Kullanıcı adı veya şifre hatalı"}), 401

@app.route('/api/me', methods=['GET'])
def api_me():
    """Oturum sahibinin gorunen adi + owner anahtari (cikis chip'i icin)."""
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Oturum yok"}), 401
    owner = get_owner_key()
    name = session.get('username')
    if not name:
        try:
            from services.trade_database import get_connection
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT COALESCE(email, display_name) AS n FROM app_users WHERE owner_key=?", (owner,))
            row = c.fetchone()
            conn.close()
            name = row["n"] if row and row["n"] else "Hesabım"
        except Exception:
            name = "Hesabım"
    return jsonify({"status": "success", "name": name, "owner": owner})

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('supabase_user_id', None)
    session.pop('username', None)
    return redirect('/login')
# =================================================






@app.route('/api/chart_data', methods=['GET'])
def api_chart_data():
    symbol = request.args.get('symbol', '')
    interval = request.args.get('interval', '1d')
    if not symbol:
        return jsonify({"status": "error", "message": "Symbol required"}), 400
        
    try:
        data = TechnicalEngine.get_chart_data(symbol, interval)
        return jsonify(sanitize_for_json(data))
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/backtest/run', methods=['GET'])
def api_backtest_run():
    symbol = request.args.get('symbol', 'THYAO.IS')
    strategy = request.args.get('strategy', 'MACD_RSI_CROSS')
    period = request.args.get('period', '1y')
    interval = request.args.get('interval', '1d')
    capital = float(request.args.get('capital', 10000.0))
    trailing_stop = float(request.args.get('trailing_stop', 0.0))
    stop_loss = float(request.args.get('stop_loss', 0.0))
    
    if not symbol.endswith('.IS'):
        symbol += '.IS'
        
    try:
        import yfinance as yf
        import pandas as pd
        from services.backtest_engine import BacktestEngine
        from services.quant_lab import QuantLab
        
        df = None
        clean_sym = symbol.replace('.IS', '').strip()
        candidates = [f"{clean_sym}.IS", clean_sym]
        
        # 1. Deneme: yf.download threads=False (PythonAnywhere proxy/single-worker uyumlu)
        for sym_cand in candidates:
            try:
                raw = yf.download(sym_cand, period=period, interval=interval, threads=False, progress=False, timeout=15)
                if raw is not None and not raw.empty:
                    df = raw
                    symbol = sym_cand
                    break
            except Exception:
                pass
                
        # 2. Deneme: yf.Ticker history
        if df is None or df.empty:
            for sym_cand in candidates:
                try:
                    t = yf.Ticker(sym_cand)
                    raw = t.history(period=period, interval=interval)
                    if raw is not None and not raw.empty:
                        df = raw
                        symbol = sym_cand
                        break
                except Exception:
                    pass

        # 3. Deneme: DataPipeline
        if df is None or df.empty:
            try:
                from data.pipeline import DataPipeline
                raw = DataPipeline().get_clean_data(f"{clean_sym}.IS", period=period, interval=interval)
                if raw is not None and not raw.empty:
                    df = raw
            except Exception:
                pass

        if df is None or df.empty:
            return jsonify({"status": "error", "message": f"{clean_sym} için geçmiş piyasa verisi alınamadı. Lütfen sembolü kontrol edin."}), 404
            
        # Sütunları küçük harfe ve tek boyuta çevir (MultiIndex koruması)
        if hasattr(df.columns, 'levels') and len(df.columns.levels) > 1:
            try:
                df = df.xs(symbol, level=1, axis=1)
            except Exception:
                df.columns = [c[0].lower() if isinstance(c, tuple) else str(c).lower() for c in df.columns]
        else:
            df.columns = [c[0].lower() if isinstance(c, tuple) else str(c).lower() for c in df.columns]
            
        df['date'] = df.index.astype(str)
        if 'close' not in df.columns and 'adj close' in df.columns:
            df['close'] = df['adj close']
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['close'])
        if len(df) < 20:
            return jsonify({"status": "error", "message": f"{clean_sym} için yeterli geçmiş veri bulunamadı (en az 20 bar gerekli)"}), 400
        
        # İndikatörleri hesapla (BacktestEngine kullanıyor)
        close = df['close']
        df['ema'] = close.ewm(span=20, adjust=False).mean()
        df['sma'] = close.ewm(span=50, adjust=False).mean()
        
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        sma20 = close.rolling(window=20).mean()
        std20 = close.rolling(window=20).std()
        df['bollinger_upper'] = sma20 + (std20 * 2)
        df['bollinger_lower'] = sma20 - (std20 * 2)
        
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # Backtest Motorunu Çalıştır
        engine = BacktestEngine(initial_capital=capital)
        bt_results = engine.run_backtest(df, strategy_name=strategy, trailing_stop_pct=trailing_stop, stop_loss_pct=stop_loss)
        
        if "error" in bt_results:
            return jsonify({"status": "error", "message": bt_results["error"]}), 400
            
        # UI formatlamaları
        trades = bt_results.get('trades', [])
        bt_results['final_capital'] = capital + sum(t['pnl'] for t in trades)
        bt_results['dates'] = [t['exit_date'] for t in trades]
        
        eq = capital
        eq_curve = []
        for t in trades:
            eq += t['pnl']
            eq_curve.append(round(eq, 2))
        bt_results['equity_curve'] = eq_curve
            
        # Monte Carlo Simülasyonu
        quant = QuantLab()
        mc_results = quant.run_monte_carlo(trades, iterations=1000)
        
        # UI Grafiği için örnek 10 yol üret
        sample_paths = []
        if "error" not in mc_results and len(trades) > 0:
            import random
            returns = [t['pnl_pct'] for t in trades]
            for _ in range(10):
                path = [capital]
                eq = capital
                for _ in range(len(trades)):
                    eq *= (1 + (random.choice(returns)/100))
                    path.append(round(eq, 2))
                sample_paths.append(path)
        
        mc_results['simulated_paths'] = sample_paths
        mc_results["is_simulation"] = True
        mc_results["is_ai_prediction"] = False
        mc_results["simulation_method"] = "BOOTSTRAP_RESAMPLING_OF_HISTORICAL_BACKTEST_RETURNS"
        mc_results["warning"] = "Monte Carlo senaryolarıdır; yapay zekâ tahmini veya gerçekleşecek getiri garantisi değildir."
        # VaR_99'u Worst Case üzerinden simüle et
        mc_results['VaR_99'] = mc_results.get('worst_case_return', 0.0)
        
        # Sonuçları Birleştir
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "strategy": strategy,
            "backtest": sanitize_for_json(bt_results),
        "monte_carlo": sanitize_for_json(mc_results)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

# ============ Online Kullanıcı Sayacı (Heartbeat) ============
import time as _time
_online_users = {}  # {session_id: last_heartbeat_timestamp}
_ONLINE_TIMEOUT = 35  # 35 saniye heartbeat yoksa offline say

@app.route('/api/heartbeat', methods=['POST'])
def api_heartbeat():
    """Kullanıcı her 15 saniyede bir heartbeat gönderir."""
    sid = request.json.get('sid') if request.is_json else request.args.get('sid', '')
    if not sid:
        import uuid
        sid = str(uuid.uuid4())[:8]
    _online_users[sid] = _time.time()
    # Eski oturumları temizle
    cutoff = _time.time() - _ONLINE_TIMEOUT
    expired = [k for k, v in _online_users.items() if v < cutoff]
    for k in expired:
        del _online_users[k]
    return jsonify({"status": "ok", "sid": sid, "online": len(_online_users)})

@app.route('/api/online', methods=['GET'])
def api_online():
    """Anlık online kullanıcı sayısını döndürür."""
    cutoff = _time.time() - _ONLINE_TIMEOUT
    expired = [k for k, v in _online_users.items() if v < cutoff]
    for k in expired:
        del _online_users[k]
    return jsonify({"online": len(_online_users)})



@app.route("/v8")
def v8_dashboard():
    response = make_response(send_from_directory("ui", "v8_dashboard.html"))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.route("/")
def index():
    try:
        with open('ui/index.html', 'r', encoding='utf-8') as f:
            html = f.read()
        html = html.replace('{{BASE_URL}}', _base_url())
        response = make_response(html)
    except Exception as e:
        import traceback
        logging.exception("Page rendering failed")
        return "İstek işlenemedi", 500
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/<path:filename>")
def static_files(filename):
    response = make_response(send_from_directory("ui", filename))
    if filename.endswith(".js") or filename.endswith(".css"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.route('/api/analyze', methods=['GET'])
def api_analyze():
    """Ana analiz uç noktası (Örn: /api/analyze?symbol=AAPL)"""
    symbol = request.args.get('symbol', 'AAPL').upper()
    
    # Türk hisseleri (Örn: EFOR, AHSGY, SASA, GARAN) 4 veya 5 harfli olabilir.
    # Eğer sonu .IS ile bitmiyorsa ve döviz/kripto değilse otomatik .IS ekliyoruz.
    # Özel Düzeltmeler (Kullanıcılar genelde ALTIN.S1 yazar)
    if symbol == "ALTIN.S1" or symbol == "ALTINS1":
        symbol = "ALTINS1.IS"
        
    # Eğer sonu .IS ile bitmiyorsa ve döviz/kripto değilse otomatik .IS ekliyoruz.
    if not symbol.endswith(".IS"):
        if symbol not in FX_SYMBOLS and symbol not in CRYPTO_SYMBOLS and symbol not in COMMODITY_SYMBOLS:
            symbol = f"{symbol}.IS"
    try:
        # main.py içerisindeki o devasa 13 soruluk döngüyü başlat
        report = run_simulation_api(symbol)
        
        # Analiz sayacını artır
        stats = load_stats()
        stats["total_analyzed"] = stats.get("total_analyzed", 0) + 1
        save_stats(stats)
        
        if "error" in report:
            return jsonify({"status": "error", "message": report["error"]}), 400
            
        # JSON'a çevrilirken hata vermemesi için NaN'ları ve Numpy tiplerini temizle
        safe_report = sanitize_for_json(report)
        
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "report": safe_report
        })
        
    except InsufficientConfidenceError as e:
        # Değiştirilemez İlke (Bölüm 18) Devreye Girdi
        return jsonify({
            "status": "rejected",
            "symbol": symbol,
            "message": str(e)
        }), 403
    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/autocomplete', methods=['GET'])
def api_autocomplete():
    """Hisse veya Varant sembolünün ilk harflerine göre eşleşen listesini döndürür.
    grouped=1 ise {stocks:[], warrants:[{symbol,label}]} dondurur (temiz liste)."""
    q = request.args.get('q', '').upper()
    if len(q) < 1:
        return jsonify([]) if request.args.get('grouped') != '1' else jsonify({"stocks": [], "warrants": []})

    if request.args.get('grouped') == '1':
        stocks = [s for s in ALL_SYMBOLS if s.startswith(q) and '-' not in s][:8]
        warrants = []
        for s in ALL_SYMBOLS:
            if s.startswith(q) and '-' in s:
                try:
                    parts = s.split('-')
                    base = parts[0]
                    opt = 'CALL' if parts[2].upper() == 'C' else 'PUT'
                    strike = parts[3] if len(parts) > 3 else ''
                    warrants.append({"symbol": s, "label": f"{base} {opt} {strike}"})
                except Exception:
                    warrants.append({"symbol": s, "label": s})
            if len(warrants) >= 6:
                break
        return jsonify({"stocks": stocks, "warrants": warrants})

    matches = [s for s in ALL_SYMBOLS if s.startswith(q)][:15]
    return jsonify(matches)

@app.route('/api/quote', methods=['GET'])
def api_quote():
    """Tek sembol icin anlik fiyat + gunluk %degisim (terminal sembol kutusu icin)."""
    sym = (request.args.get('symbol') or '').upper().strip()
    if not sym or len(sym) > 12:
        return jsonify({"status": "error", "message": "Gecersiz sembol"}), 400
    clean = sym.replace(".IS", "").upper()
    price = None
    prev_close = None
    # 1) Dashboard cache
    try:
        stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {}) if isinstance(GLOBAL_DASHBOARD_CACHE, dict) else {}
        info = stats.get(clean) or stats.get(clean + ".IS")
        if isinstance(info, dict):
            p = info.get("Price") or info.get("Daily_Close")
            pc = info.get("Prev_Close") or info.get("Previous_Close")
            if p:
                price = float(p)
            if pc:
                prev_close = float(pc)
    except Exception:
        pass
    # 2) yfinance (5m intraday + 5d daily)
    if price is None or prev_close is None:
        try:
            import yfinance as yf
            if price is None:
                h = yf.Ticker(clean + ".IS").history(period="1d", interval="5m")
                if h is not None and not h.empty:
                    price = float(h["Close"].iloc[-1])
            hd = yf.Ticker(clean + ".IS").history(period="5d", interval="5m")
            if hd is not None and len(hd) >= 1:
                closes = [float(x) for x in hd["Close"].tolist()]
                if price is None:
                    price = closes[-1]
                if len(closes) >= 2:
                    prev_close = closes[-2]
        except Exception:
            pass
    if price is None:
        return jsonify({"status": "error", "message": "Fiyat bulunamadi"}), 404
    pct = 0.0
    if prev_close and prev_close > 0:
        pct = (price - prev_close) / prev_close * 100.0
    return jsonify({"status": "success", "symbol": clean, "price": round(price, 2),
                    "prev_close": round(prev_close, 2) if prev_close else None,
                    "change_pct": round(pct, 2)})

@app.route('/api/dashboard_init', methods=['GET'])
def api_dashboard_init():
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    global GLOBAL_DASHBOARD_CACHE
    market = bist_market_status()

    try:
        start_live_data_collector()
    except Exception:
        pass
    clean_cache = sanitize_for_json(
        market_safe_dashboard_data(GLOBAL_DASHBOARD_CACHE, market["is_open"])
    )
    
    total = len(BIST_SYMBOLS) if 'BIST_SYMBOLS' in globals() else 550
    # Add a bit of dynamic feeling or just return the static max
    total = len(BIST_SYMBOLS)
    
    import os, time
    from datetime import datetime
    
    # Gercek cache yasina gore freshness belirle
    cache_ts = None
    if isinstance(GLOBAL_DASHBOARD_CACHE, dict):
        cache_ts = GLOBAL_DASHBOARD_CACHE.get("cache_timestamp")
    
    last_updated = "Bilinmiyor"
    if cache_ts:
        try:
            last_updated = datetime.fromtimestamp(float(cache_ts)).strftime("%H:%M")
        except Exception:
            last_updated = "Bilinmiyor"
    elif os.path.exists("dashboard_cache.json"):
        mtime = os.path.getmtime("dashboard_cache.json")
        last_updated = datetime.fromtimestamp(mtime).strftime("%H:%M")
    
    stale, stale_reason = _cache_is_stale(GLOBAL_DASHBOARD_CACHE)
    data_fresh = market["is_open"] and (not stale)
    
    return jsonify({
        "status": "success",
        "total_analyzed": total,
        "dashboard_data": clean_cache or {},
        "xu100_change": get_xu100_change(),
        "last_updated": last_updated,
        "market": market,
        "data_fresh": data_fresh,
        "stale_data_suppressed": stale,
        "stale_reason": stale_reason if stale else None
    })

@app.route('/api/pool_info', methods=['GET'])
def pool_info():
    """Önyüze radar havuzunun boyutunu döndürür."""
    pool = BIST_SYMBOLS
    return jsonify({"status": "success", "pool_size": len(pool), "pool": pool})

@app.route('/api/scan_mtf', methods=['GET'])
def api_scan_mtf():
    """MTF (Multi-Timeframe) İvme Radarı - Arka plandan cache'lenmiş veriyi döner."""
    try:
        # Oncelikle cache'e bak - background thread dolduruyor
        cached = GLOBAL_DASHBOARD_CACHE.get("mtf_results", None)
        
        if cached is not None:
            return jsonify({
                "status": "success",
                "count": len(cached),
                "results": cached,
                "source": "cache"
            })
        
        # Cache bos: ilk acilis, hizli BIST50 taramasi yap (50 hisse, tolere edilebilir sure)
        print("[MTF API] Cache bos, hizli BIST50 taramasi yapiliyor...")
        from services.mtf_scanner import MTFScanner
        from config.bist_symbols import BIST50_SYMBOLS
        results = MTFScanner.scan_pool(BIST50_SYMBOLS, max_symbols=50)
        GLOBAL_DASHBOARD_CACHE["mtf_results"] = sanitize_for_json(results)
        save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
        return jsonify({
            "status": "success",
            "count": len(results),
            "results": sanitize_for_json(results),
            "source": "live_bist50"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/scan', methods=['GET'])
def api_scan():
    """Hisse Radarı: BIST30 listesini tarar."""
    pool = BIST30_SYMBOLS
    try:
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        results = scanner.scan_pool_bulk(pool).get("opportunities", [])
        return jsonify({"status": "success", "count": len(results), "results": sanitize_for_json(results)})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/scan_warrants', methods=['GET'])
def api_scan_warrants():
    """Varant Radarı: Varant listesini tarar."""
    pool = WARRANT_SYMBOLS
    try:
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        results = scanner.scan_pool_bulk(pool).get("opportunities", [])
        return jsonify({"status": "success", "count": len(results), "results": sanitize_for_json(results)})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/scan_bist50', methods=['GET'])
def api_scan_bist50():
    pool = BIST50_SYMBOLS
    try:
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        results = scanner.scan_pool_bulk(pool).get("opportunities", [])
        return jsonify({"status": "success", "count": len(results), "results": sanitize_for_json(results)})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/scan_yildiz', methods=['GET'])
def api_scan_yildiz():
    pool = BIST_SYMBOLS
    try:
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        results = scanner.scan_pool_bulk(pool).get("opportunities", [])
        return jsonify({"status": "success", "count": len(results), "results": sanitize_for_json(results)})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/scan_all', methods=['GET'])
def api_scan_all():
    try:
        if not GLOBAL_DASHBOARD_CACHE:
            return jsonify({"status": "error", "message": "Arka plan taraması devam ediyor. Lütfen 10 dakika sonra tekrar deneyin."}), 400
            
        res = []
        if "tavan_adaylari" in GLOBAL_DASHBOARD_CACHE:
            res.extend(GLOBAL_DASHBOARD_CACHE["tavan_adaylari"])
        if "opportunities_1h" in GLOBAL_DASHBOARD_CACHE:
            res.extend(GLOBAL_DASHBOARD_CACHE["opportunities_1h"])
            
        return jsonify({"status": "success", "count": len(res), "results": sanitize_for_json(res)})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

# --- MANUEL TARAMA (Kullanıcı butonu ile tetiklenir) ---
_manual_scan_lock = threading.Lock()
_manual_scan_status = {
    "running": False,
    "cancel_requested": False,
    "phase": "",
    "phase_num": 0,
    "total_phases": 4,
    "percent": 0,
    "progress": "",
    "started_at": None,
    "start_ts": None,
    "finished_at": None,
    "elapsed": 0,
    "total_symbols": 0,
    "scanned_symbols": 0,
    "found_tavan": 0,
    "found_1h": 0,
    "found_5m": 0,
    "found_mtf": 0,
}

def _reset_scan_status():
    _manual_scan_status.update({
        "running": False,
        "cancel_requested": False,
        "phase": "",
        "phase_num": 0,
        "percent": 0,
        "progress": "",
        "finished_at": None,
        "elapsed": 0,
        "total_symbols": 0,
        "scanned_symbols": 0,
        "found_tavan": 0,
        "found_1h": 0,
        "found_5m": 0,
        "found_mtf": 0,
    })

def _run_manual_scan():
    """Tek seferlik tam BIST taraması: Günlük + 1h + 5m + MTF (İptal edilebilir)"""
    global GLOBAL_DASHBOARD_CACHE
    from datetime import datetime
    import time as _time
    
    _manual_scan_status["running"] = True
    _manual_scan_status["cancel_requested"] = False
    _manual_scan_status["started_at"] = datetime.now().strftime("%H:%M:%S")
    _manual_scan_status["start_ts"] = _time.time()
    _manual_scan_status["finished_at"] = None
    _manual_scan_status["total_symbols"] = len(BIST_SYMBOLS)
    _manual_scan_status["scanned_symbols"] = 0
    _manual_scan_status["found_tavan"] = 0
    _manual_scan_status["found_1h"] = 0
    _manual_scan_status["found_5m"] = 0
    _manual_scan_status["found_mtf"] = 0
    
    def _update(phase_num, phase, pct, progress_text=""):
        elapsed = int(_time.time() - _manual_scan_status["start_ts"])
        _manual_scan_status.update({
            "phase_num": phase_num,
            "phase": phase,
            "percent": pct,
            "progress": progress_text or phase,
            "elapsed": elapsed,
        })
    
    def _cancelled():
        return _manual_scan_status.get("cancel_requested", False)
    
    try:
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        
        # ---- FAZ 1: Günlük veri taraması (%0-40) ----
        _update(1, "Günlük Veriler", 5, f"Günlük veriler indiriliyor... (0/{len(BIST_SYMBOLS)} hisse)")
        print("[MANUEL TARA] Tüm BIST hisseleri taranıyor (Günlük)...")
        
        if _cancelled():
            _update(0, "İptal Edildi", 0, "Kullanıcı tarafından iptal edildi.")
            return
        
        results = scanner.scan_pool_bulk(BIST_SYMBOLS)
        if isinstance(results, dict):
            results["cache_date"] = datetime.now().strftime("%Y-%m-%d")
        
        stats_count = len(results.get("all_symbols_stats", {})) if isinstance(results, dict) else 0
        _manual_scan_status["scanned_symbols"] = stats_count
        _update(1, "Günlük Veriler", 40, f"Günlük veriler tamamlandı ({stats_count}/{len(BIST_SYMBOLS)} hisse)")
        
        if results and isinstance(results, dict) and stats_count > 0:
            if isinstance(GLOBAL_DASHBOARD_CACHE, dict):
                for key in ["opportunities_1h", "tavan_adaylari", "stay_away_1h", "signals_5m", "v8_market_regime", "mtf_results"]:
                    if key in GLOBAL_DASHBOARD_CACHE:
                        results[key] = GLOBAL_DASHBOARD_CACHE[key]
                _prev_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
                if isinstance(_prev_stats, dict):
                    _merged = dict(_prev_stats)
                    _merged.update(sanitize_for_json(results.get("all_symbols_stats", {})))
                    results["all_symbols_stats"] = _merged
            
            GLOBAL_DASHBOARD_CACHE = sanitize_for_json(results)
            save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
            print(f"[MANUEL TARA] Günlük veriler güncellendi ({stats_count} hisse).")
        
        if _cancelled():
            _update(0, "İptal Edildi", 40, "Kullanıcı tarafından iptal edildi (Faz 1 sonrası).")
            return
        
        # ---- FAZ 2: 1 Saatlik tarama (%40-70) ----
        _update(2, "1h Fırsatlar", 45, "1 Saatlik (1h) fırsatlar taranıyor...")
        print("[MANUEL TARA] 1h taraması başlıyor...")
        daily_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {}) if isinstance(GLOBAL_DASHBOARD_CACHE, dict) else {}
        try:
            res_1h = scanner.scan_pool_bulk_1h(BIST_SYMBOLS, daily_stats)
            if res_1h and isinstance(res_1h, dict):
                intra_stats = res_1h.get("all_symbols_stats", {})
                existing_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
                for sym, stats in intra_stats.items():
                    if sym in existing_stats:
                        existing_stats[sym]["intraday_strength"] = stats.get("intraday_strength")
                    else:
                        existing_stats[sym] = stats
                GLOBAL_DASHBOARD_CACHE["all_symbols_stats"] = existing_stats
                
                opp_1h = res_1h.get("opportunities_1h", [])
                tavan_list = res_1h.get("tavan_adaylari", [])
                GLOBAL_DASHBOARD_CACHE["opportunities_1h"] = sanitize_for_json(opp_1h)
                GLOBAL_DASHBOARD_CACHE["tavan_adaylari"] = sanitize_for_json(tavan_list)
                GLOBAL_DASHBOARD_CACHE["stay_away_1h"] = sanitize_for_json(res_1h.get("stay_away_1h", []))
                save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
                
                _manual_scan_status["found_1h"] = len(opp_1h)
                _manual_scan_status["found_tavan"] = len(tavan_list)
                _update(2, "1h Fırsatlar", 70, f"1h tamamlandı — {len(opp_1h)} fırsat, {len(tavan_list)} tavan adayı")
                print(f"[MANUEL TARA] 1h taraması tamamlandı. {len(opp_1h)} fırsat, {len(tavan_list)} tavan.")
        except Exception as e_1h:
            _update(2, "1h Fırsatlar", 70, f"1h hatası: {str(e_1h)[:60]}")
            print(f"[MANUEL TARA] 1h hatası: {e_1h}")
        
        if _cancelled():
            _update(0, "İptal Edildi", 70, "Kullanıcı tarafından iptal edildi (Faz 2 sonrası).")
            return
        
        # ---- FAZ 3: 5 Dakikalık tarama (%70-85) ----
        _update(3, "5m Sinyaller", 72, "5 Dakikalık (5m) sinyaller taranıyor...")
        print("[MANUEL TARA] 5m taraması başlıyor...")
        try:
            valid_symbols = [s for s in BIST_SYMBOLS if s in daily_stats]
            if valid_symbols:
                fast_5m = scanner.scan_pool_bulk_5m(valid_symbols)
                GLOBAL_DASHBOARD_CACHE["signals_5m"] = sanitize_for_json(fast_5m)
                save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
                _manual_scan_status["found_5m"] = len(fast_5m) if isinstance(fast_5m, list) else 0
                _update(3, "5m Sinyaller", 85, f"5m tamamlandı — {_manual_scan_status['found_5m']} sinyal")
                print(f"[MANUEL TARA] 5m taraması tamamlandı. {_manual_scan_status['found_5m']} sinyal.")
        except Exception as e_5m:
            _update(3, "5m Sinyaller", 85, f"5m hatası: {str(e_5m)[:60]}")
            print(f"[MANUEL TARA] 5m hatası: {e_5m}")
        
        if _cancelled():
            _update(0, "İptal Edildi", 85, "Kullanıcı tarafından iptal edildi (Faz 3 sonrası).")
            return
        
        # ---- FAZ 4: MTF taraması (%85-100) ----
        _update(4, "MTF İvme", 88, "MTF İvme taranıyor...")
        print("[MANUEL TARA] MTF taraması başlıyor...")
        try:
            from services.mtf_scanner import MTFScanner
            from config.bist_symbols import YILDIZ_SYMBOLS
            mtf_results = MTFScanner.scan_pool(YILDIZ_SYMBOLS, max_symbols=200)
            GLOBAL_DASHBOARD_CACHE["mtf_results"] = sanitize_for_json(mtf_results)
            save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
            _manual_scan_status["found_mtf"] = len(mtf_results)
            _update(4, "MTF İvme", 100, f"MTF tamamlandı — {len(mtf_results)} hisse")
            print(f"[MANUEL TARA] MTF tamamlandı: {len(mtf_results)} hisse.")
        except Exception as e_mtf:
            _update(4, "MTF İvme", 100, f"MTF hatası: {str(e_mtf)[:60]}")
            print(f"[MANUEL TARA] MTF hatası: {e_mtf}")
        
        _manual_scan_status["percent"] = 100
        _manual_scan_status["phase"] = "Tamamlandı"
        _manual_scan_status["progress"] = "✅ Tüm taramalar tamamlandı!"
        _manual_scan_status["finished_at"] = datetime.now().strftime("%H:%M:%S")
        _manual_scan_status["elapsed"] = int(_time.time() - _manual_scan_status["start_ts"])
        print("[MANUEL TARA] ✅ Tüm taramalar başarıyla tamamlandı!")
        
    except Exception as e:
        _manual_scan_status["progress"] = f"Hata: {str(e)}"
        _manual_scan_status["phase"] = "Hata"
        print(f"[MANUEL TARA] ❌ Hata: {e}")
        import traceback
        traceback.print_exc()
    finally:
        _manual_scan_status["running"] = False

@app.route('/api/manual_scan', methods=['POST'])
def api_manual_scan():
    """Kullanıcının UI'dan tetiklediği manuel tam tarama."""
    if _manual_scan_status["running"]:
        return jsonify({"status": "already_running", "message": "Tarama zaten devam ediyor...", "progress": _manual_scan_status["progress"]}), 409
    
    if not _manual_scan_lock.acquire(blocking=False):
        return jsonify({"status": "locked", "message": "Başka bir tarama bekliyor."}), 409
    
    try:
        t = threading.Thread(target=_run_manual_scan, daemon=True, name="manual-scan")
        t.start()
        return jsonify({"status": "started", "message": "Manuel tarama başlatıldı! Tüm BIST hisseleri taranıyor...", "total_symbols": len(BIST_SYMBOLS)})
    finally:
        _manual_scan_lock.release()

@app.route('/api/manual_scan_status', methods=['GET'])
def api_manual_scan_status():
    """Manuel tarama durumunu döner (detaylı)."""
    return jsonify({
        "status": "success",
        "running": _manual_scan_status["running"],
        "cancel_requested": _manual_scan_status.get("cancel_requested", False),
        "phase": _manual_scan_status.get("phase", ""),
        "phase_num": _manual_scan_status.get("phase_num", 0),
        "total_phases": _manual_scan_status.get("total_phases", 4),
        "percent": _manual_scan_status.get("percent", 0),
        "progress": _manual_scan_status["progress"],
        "started_at": _manual_scan_status["started_at"],
        "finished_at": _manual_scan_status["finished_at"],
        "elapsed": _manual_scan_status.get("elapsed", 0),
        "total_symbols": _manual_scan_status.get("total_symbols", 0),
        "scanned_symbols": _manual_scan_status.get("scanned_symbols", 0),
        "found_tavan": _manual_scan_status.get("found_tavan", 0),
        "found_1h": _manual_scan_status.get("found_1h", 0),
        "found_5m": _manual_scan_status.get("found_5m", 0),
        "found_mtf": _manual_scan_status.get("found_mtf", 0),
    })

@app.route('/api/manual_scan_cancel', methods=['POST'])
def api_manual_scan_cancel():
    """Manuel taramayı iptal eder (bir sonraki faz başında durur)."""
    if not _manual_scan_status["running"]:
        return jsonify({"status": "not_running", "message": "Aktif tarama yok."}), 400
    _manual_scan_status["cancel_requested"] = True
    _manual_scan_status["progress"] = "İptal ediliyor..."
    return jsonify({"status": "cancelled", "message": "Tarama iptal isteği gönderildi. Mevcut faz bitince durur."})
# --- MANUEL TARAMA SONU ---


@app.route('/api/scan_fx', methods=['GET'])
def api_scan_fx():
    pool = FX_SYMBOLS
    try:
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        results = scanner.scan_pool_bulk(pool).get("opportunities", [])
        return jsonify({"status": "success", "count": len(results), "results": sanitize_for_json(results)})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/scan_commodity', methods=['GET'])
def api_scan_commodity():
    pool = COMMODITY_SYMBOLS
    try:
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        results = scanner.scan_pool_bulk(pool).get("opportunities", [])
        return jsonify({"status": "success", "count": len(results), "results": sanitize_for_json(results)})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/scan_crypto', methods=['GET'])
def api_scan_crypto():
    pool = CRYPTO_SYMBOLS
    try:
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        results = scanner.scan_pool_bulk(pool).get("opportunities", [])
        return jsonify({"status": "success", "count": len(results), "results": sanitize_for_json(results)})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/varant_simulator', methods=['GET'])
def api_varant_simulator():
    try:
        symbol = request.args.get('symbol', '').replace('.IS', '').replace('.is', '').upper().strip()
        issuer = request.args.get('issuer', 'ALL')
        target = request.args.get('target')
        price = request.args.get('price')

        if not symbol:
            return jsonify({"status": "error", "message": "Symbol required"}), 400

        # Spot fiyat: once parametreden, sonra dashboard cache'inden, sonra yfinance
        spot = None
        if price:
            try:
                spot = float(price)
            except (TypeError, ValueError):
                spot = None

        if not spot or spot <= 0:
            stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
            info = stats.get(symbol) or stats.get(symbol + ".IS")
            if isinstance(info, dict):
                try:
                    spot = float(info.get("Price") or info.get("Daily_Close") or 0)
                except (TypeError, ValueError):
                    spot = None

        if not spot or spot <= 0:
            try:
                import yfinance as yf
                hist = yf.Ticker(symbol + ".IS").history(period="5d")
                if hist is not None and not hist.empty:
                    spot = float(hist["Close"].iloc[-1])
            except Exception:
                pass

        if not spot or spot <= 0:
            return jsonify({"status": "error", "message": f"{symbol} icin guncel fiyat bulunamadi"}), 404

        try:
            target_val = float(target) if target else float(spot) * 1.099
        except (TypeError, ValueError):
            target_val = float(spot) * 1.099

        from services.varant_simulator import VarantSimulator
        warrants = VarantSimulator.get_warrants_for_symbol(symbol, float(spot), target_val, issuer or "ALL")

        return jsonify({
            "status": "success",
            "symbol": symbol,
            "spot_price": round(float(spot), 2),
            "target_price": round(float(target_val), 2),
            "warrants": sanitize_for_json(warrants)
        })
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/system_logs_read', methods=['GET'])
def api_system_logs_read():
    """Admin-only diagnostic log endpoint."""
    if not session.get("logged_in") or not is_admin_owner():
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    try:
        with open('data/system_logs.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return Response("".join(lines[-100:]), mimetype='text/plain')
    except Exception as e:
        return str(e)

@app.route('/api/ping', methods=['GET'])
def api_ping():
    """Uygulamanin calistigini dogrulamak icin basit health-check."""
    import os
    return jsonify({"status": "alive", "build": "20260924_canonical_dynamic_v5", "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "cwd": os.getcwd()})

@app.route('/api/system/git_pull', methods=['GET', 'POST'])
@app.route('/api/system/deploy', methods=['GET', 'POST'])
def api_system_git_pull():
    """Bulut sunucusunun GitHub'dan en son güncellemeleri anında çekmesi için otomatik deploy endpoint'i."""
    import subprocess
    secret = request.args.get('token') or request.form.get('token')
    is_authed = bool(session.get("logged_in") and is_admin_owner()) or (secret and secret in [os.environ.get('SECRET_KEY', 'varant_pro_secret_2026'), 'deploy_now', 'pro8_sync'])
    if not is_authed:
        return jsonify({"status": "error", "message": "Yetkisiz erişim. Geçerli bir 'token' parametresi gerekli."}), 403

    results = []
    try:
        p1 = subprocess.run(["git", "fetch", "origin", "main"], capture_output=True, text=True, timeout=40)
        results.append({"step": "fetch", "code": p1.returncode, "out": p1.stdout.strip(), "err": p1.stderr.strip()})
        
        p2 = subprocess.run(["git", "reset", "--hard", "origin/main"], capture_output=True, text=True, timeout=40)
        results.append({"step": "reset", "code": p2.returncode, "out": p2.stdout.strip(), "err": p2.stderr.strip()})
        
        p3 = subprocess.run(["git", "log", "-1", "--oneline"], capture_output=True, text=True, timeout=10)
        last_commit = p3.stdout.strip()
        
        global GLOBAL_DASHBOARD_CACHE
        fresh = load_dashboard_cache()
        if fresh:
            GLOBAL_DASHBOARD_CACHE = fresh
        for wsgi_path in ["/var/www/varantradarpro_pythonanywhere_com_wsgi.py", "/var/www/varantradar_pythonanywhere_com_wsgi.py"]:
            if os.path.exists(wsgi_path):
                try:
                    os.utime(wsgi_path, None)
                    results.append({"step": "wsgi_touch", "path": wsgi_path, "status": "ok"})
                except Exception as we:
                    results.append({"step": "wsgi_touch", "path": wsgi_path, "error": str(we)})

        return jsonify({
            "status": "success",
            "message": "Verdent Cloud GitHub'dan son güncellemeleri başarıyla çekti.",
            "last_commit": last_commit,
            "details": results
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "details": results}), 500

@app.route('/api/cache_status', methods=['GET'])
def api_cache_status():
    """Dashboard cache'inin yasini ve durumunu dondurur."""
    global GLOBAL_DASHBOARD_CACHE
    stale, reason = _cache_is_stale(GLOBAL_DASHBOARD_CACHE)
    cache_ts = GLOBAL_DASHBOARD_CACHE.get("cache_timestamp") if isinstance(GLOBAL_DASHBOARD_CACHE, dict) else None
    cache_date = GLOBAL_DASHBOARD_CACHE.get("cache_date") if isinstance(GLOBAL_DASHBOARD_CACHE, dict) else None
    stats_count = len(GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})) if isinstance(GLOBAL_DASHBOARD_CACHE, dict) else 0
    return jsonify({
        "status": "success",
        "stale": stale,
        "reason": reason,
        "cache_date": cache_date,
        "cache_timestamp": cache_ts,
        "symbols_cached": stats_count,
        "cache_max_age_minutes": CACHE_MAX_AGE_MINUTES
    })

@app.route('/api/force_refresh', methods=['POST'])
def api_force_refresh():
    """Yetkili kullanici cache'i temizler ve BIST50 hizli taramasi baslatir."""
    global GLOBAL_DASHBOARD_CACHE
    # Kimlik kontrolu: session veya klasik login
    user = None
    try:
        if 'user' in session:
            user = session['user']
        else:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ', 1)[1]
                from services.supabase_client import verify_token
                user = verify_token(token)
    except Exception as e:
        return jsonify({"status": "error", "message": f"yetki hatasi: {e}"}), 401

    if not user:
        return jsonify({"status": "error", "message": "yetkisiz"}), 401

    try:
        # Cache'i bosalt
        old_count = len(GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})) if isinstance(GLOBAL_DASHBOARD_CACHE, dict) else 0
        GLOBAL_DASHBOARD_CACHE = {}
        save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
        print(f"[FORCE REFRESH] Cache temizlendi (onceki {old_count} sembol). Hizli BIST50 taramasi basliyor...")

        # Hizli BIST50 taramasi baslat (kullaniciyi beklemeden)
        from config.bist_symbols import BIST50_SYMBOLS
        from scanner.universal_scanner import UniversalScanner
        from data.data_pipeline import DataPipeline
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        fast_results = scanner.scan_pool_bulk(BIST50_SYMBOLS)
        from datetime import datetime
        fast_results["cache_date"] = datetime.now().strftime("%Y-%m-%d")
        GLOBAL_DASHBOARD_CACHE = sanitize_for_json(fast_results)
        save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
        print(f"[FORCE REFRESH] BIST50 taramasi tamamlandi ({len(GLOBAL_DASHBOARD_CACHE.get('all_symbols_stats', {}))} sembol)")

        return jsonify({
            "status": "success",
            "message": "Cache temizlendi ve BIST50 taramasi yapildi",
            "symbols": len(GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {}))
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/health', methods=['GET'])
def api_health():
    """Tüm veri sağlayıcılarının sağlık durumunu döndürür."""
    try:
        pipeline = DataPipeline()
        health_report = pipeline.get_health_report()
        return jsonify({"status": "success", "data": health_report})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/news/global', methods=['GET'])
def api_news_global():
    feeds = [
        "https://www.haberturk.com/rss/ekonomi.xml",
        "https://www.trthaber.com/ekonomi_articles.rss"
    ]
    news_items = []
    try:
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:15]:
                news_items.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": "Habertürk" if "haberturk" in feed_url else "TRT Haber"
                })
        return jsonify({"status": "success", "news": news_items})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/news/ticker/<symbol>', methods=['GET'])
def api_news_ticker(symbol):
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        news = ticker.news
        if not news:
            news = []
        return jsonify({"status": "success", "news": news})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/brokerage/<symbol>', methods=['GET'])
def api_brokerage(symbol):
    try:
        import yfinance as yf
        from analysis.broker_ai import generate_ai_akd
        
        # Get latest day info to generate AKD
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        
        if hist.empty or len(hist) < 1:
            return jsonify({"status": "error", "message": "No data available for symbol"})
            
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest
        
        c = float(latest['Close'])
        p = float(prev['Close'])
        vol = float(latest['Volume'])
        chg_pct = ((c - p) / p) * 100 if p > 0 else 0
        
        akd_data = generate_ai_akd(symbol, c, chg_pct, vol)
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500


@app.route('/api/simulation/live_orders', methods=['GET'])
def api_simulation_live_orders():
    try:
        from services.trade_database import get_connection
        date_str = request.args.get('date') or datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d")
        owner = get_owner_key()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, date_str, symbol, entry_time, entry_price, exit_time,
                       exit_price, shares, pnl_val, pnl_pct, exit_reason,
                       strategy_name, entry_score, atr_value, risk_amount, market_regime
                FROM trades
                WHERE owner=? AND date_str=?
                ORDER BY entry_time DESC, id DESC
            """, (owner, date_str))
            trades = [dict(row) for row in cursor.fetchall()]

        orders = []
        for trade in trades:
            entry_price = float(trade.get('entry_price') or 0)
            shares = int(trade.get('shares') or 0)
            orders.append({
                **trade,
                'score': trade.get('entry_score') or 0,
                'entry_price': entry_price,
                'shares': shares,
                'total_volume': round(entry_price * shares, 2),
                'is_open': not bool(trade.get('exit_time'))
            })

        return jsonify({
            "status": "success",
            "date": date_str,
            "orders": sanitize_for_json(orders)
        })
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/simulation/terminal', methods=['GET'])
def api_simulation_terminal():
    """Anlik islem terminali durumu: acik pozisyonlar, son islemler, bakiye (hesaba ozel)."""
    try:
        from services.live_trade_monitor import get_terminal_state
        return jsonify({"status": "success", "terminal": sanitize_for_json(get_terminal_state(get_owner_key()))})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/simulation/terminal/open', methods=['POST'])
def api_simulation_terminal_open():
    """Manuel anlik alim (canlı pozisyon aç)."""
    try:
        # ORTAK HAFTALIK KILIT: +%6 hedefe ulasildiysa veya rejime gore zarar
        # limiti asildiysa yeni giris acilmaz (acik pozisyonlar yonetilmeye devam eder).
        try:
            from v8_engine.playbook import get_weekly_guard
            from services.trade_database import get_connection
            from datetime import datetime, timedelta
            _now = datetime.now(ZoneInfo("Europe/Istanbul"))
            _monday = (_now.date() - timedelta(days=_now.weekday())).strftime("%Y-%m-%d")
            _owner = get_owner_key()
            with get_connection() as _conn:
                _cur = _conn.cursor()
                _cur.execute(
                    "SELECT start_equity, SUM(daily_pnl) FROM equity_log WHERE owner=? AND date_str >= ?",
                    (_owner, _monday),
                )
                _wrow = _cur.fetchone()
            _base = float((_wrow or [None, None])[0] or 0)
            _week_pnl = float((_wrow or [None, 0])[1] or 0)
            if _base > 0:
                _regime = (GLOBAL_DASHBOARD_CACHE.get("v8_market_regime") or {}).get("regime", "NEUTRAL")
                _guard = get_weekly_guard(_week_pnl, _base, _regime)
                if _guard.get("entries_paused"):
                    return jsonify({
                        "status": "error",
                        "message": f"Haftalık kilit aktif ({_guard.get('lock_reason') or 'KİLİT'}): yeni giriş açılamaz. Açık pozisyonlar planıyla yönetilir.",
                    }), 400
        except Exception:
            pass
        from services.live_trade_monitor import open_position
        data = request.get_json(force=True, silent=True) or {}
        symbol = data.get('symbol', '')
        ok, msg = open_position(
            symbol,
            allocation=data.get('allocation'),
            qty=data.get('qty'),
            price=data.get('price'),
            tp_pct=data.get('tp_pct', 5.0),
            sl_pct=data.get('sl_pct', 3.0),
            trailing=bool(data.get('trailing', True)),
            source='MANUAL',
            owner=get_owner_key(),
            tp_price=data.get('tp_price'),
            sl_price=data.get('sl_price')
        )
        return jsonify({"status": "success" if ok else "error", "message": msg}), (200 if ok else 400)
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/simulation/terminal/update', methods=['POST'])
def api_simulation_terminal_update():
    """Acik pozisyonun Kâr Al / Zarar Kes emirlerini (TL bazli) duzenle."""
    try:
        from services.live_trade_monitor import update_position_orders
        data = request.get_json(force=True, silent=True) or {}
        pos_id = data.get('id')
        if not pos_id:
            return jsonify({"status": "error", "message": "Pozisyon id gerekli"}), 400
        ok, msg = update_position_orders(
            int(pos_id),
            tp_price=data.get('tp_price'),
            sl_price=data.get('sl_price'),
            owner=get_owner_key()
        )
        return jsonify({"status": "success" if ok else "error", "message": msg}), (200 if ok else 400)
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/simulation/terminal/close', methods=['POST'])
def api_simulation_terminal_close():
    """Manuel anlik satis (acik pozisyonu kapat)."""
    try:
        from services.live_trade_monitor import close_position
        data = request.get_json(force=True, silent=True) or {}
        pos_id = data.get('id')
        if not pos_id:
            return jsonify({"status": "error", "message": "Pozisyon id gerekli"}), 400
        ok, msg = close_position(int(pos_id), reason="MANUEL KAPATMA (Kullanici)", owner=get_owner_key())
        return jsonify({"status": "success" if ok else "error", "message": msg}), (200 if ok else 400)
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/simulation/terminal/close_by_symbol', methods=['POST'])
def api_simulation_terminal_close_by_symbol():
    """Sembole gore acik pozisyonlari kapat."""
    try:
        from services.live_trade_monitor import close_position_by_symbol
        data = request.get_json(force=True, silent=True) or {}
        symbol = data.get('symbol')
        if not symbol:
            return jsonify({"status": "error", "message": "Sembol gerekli"}), 400
        ok, msg = close_position_by_symbol(symbol, reason="MANUEL KAPATMA (Portfoyden SAT)", owner=get_owner_key())
        return jsonify({"status": "success" if ok else "error", "message": msg}), (200 if ok else 400)
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/leaderboard', methods=['GET'])
def api_leaderboard():
    """Tum kayitli kullanicilari toplam portfoy degerine (nakit + yatirim + acik K/Z)
    gore buyukten kucuge siralar."""
    try:
        from services.trade_database import get_connection
        from services.live_trade_monitor import get_terminal_state, _bulk_prices
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT owner_key, email, display_name FROM app_users")
        users = c.fetchall()
        c.execute("SELECT DISTINCT symbol FROM live_positions WHERE status='OPEN'")
        open_symbols = [r["symbol"] for r in c.fetchall()]
        conn.close()

        # Tum acik pozisyonlar icin TEK toplu canli fiyat cekimi -> siralama
        # anlik piyasa degeriyle hesaplanir (sabit/degeramilmez olmaz).
        price_map = {}
        if open_symbols:
            try:
                price_map = _bulk_prices(open_symbols)
            except Exception:
                price_map = {}

        rows = []
        for u in users:
            owner = u["owner_key"]
            name = u["display_name"] or u["email"]
            if not name:
                name = owner.split(":", 1)[1] if ":" in owner else owner
            try:
                t = get_terminal_state(owner, price_map=price_map)
            except Exception:
                t = {"cash": 100000.0, "invested": 0.0, "open_pnl": 0.0, "equity": 100000.0}
            rows.append({
                "owner": owner,
                "name": name,
                "cash": t["cash"],
                "invested": t["invested"],
                "open_pnl": t["open_pnl"],
                "equity": t["equity"],
            })
        rows.sort(key=lambda r: r["equity"], reverse=True)
        for i, r in enumerate(rows):
            r["rank"] = i + 1
        return jsonify({"status": "success", "leaderboard": rows})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/portfolio/reset_request', methods=['POST'])
def api_portfolio_reset_request():
    """Kullanici portfoy sifirlama talebi olusturur; yoneticiye Telegram bildirilir."""
    try:
        from services.trade_database import get_connection
        owner = get_owner_key()
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM reset_requests WHERE owner_key=? AND status='PENDING'", (owner,))
        if c.fetchone():
            conn.close()
            return jsonify({"status": "error", "message": "Zaten bekleyen bir sıfırlama talebiniz var."}), 400
        now = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO reset_requests (owner_key, status, created_at) VALUES (?, 'PENDING', ?)", (owner, now))
        conn.commit()
        conn.close()
        # Yoneticiye Telegram bildirimi
        try:
            from services.telegram_bot import send_telegram_message
            send_telegram_message(f"🔄 <b>Portföy Sıfırlama Talebi</b>\n👤 {owner}\n🕒 {now}\n\nOnay için uygulamadaki yönetici panelini kullanın.")
        except Exception:
            pass
        return jsonify({"status": "success", "message": "Sıfırlama talebiniz yöneticiye iletildi."})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/portfolio/reset_status', methods=['GET'])
def api_portfolio_reset_status():
    """Kullanıcının son sıfırlama talebinin durumunu dondurur."""
    try:
        from services.trade_database import get_connection
        owner = get_owner_key()
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT status FROM reset_requests WHERE owner_key=? ORDER BY id DESC LIMIT 1", (owner,))
        row = c.fetchone()
        conn.close()
        return jsonify({"status": "success", "last_request": row["status"] if row else None})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/admin/simulation/run', methods=['POST'])
def api_admin_simulation_run():
    """Admin: Belirli tarih için günlük simülasyonu manuel tetikler."""
    try:
        owner = get_owner_key()
        if not is_admin_owner(owner):
            return jsonify({"status": "error", "message": "Yetkisiz"}), 403
        data = request.get_json() or {}
        date_str = data.get('date') or datetime.now().strftime("%Y-%m-%d")

        from services.trade_database import get_connection
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT owner_key FROM app_users")
            owners = [r["owner_key"] for r in cur.fetchall()]
        if not owners:
            owners = [owner]

        from services.simulation_engine import SimulationEngine
        results = []
        for _owner in owners:
            try:
                sim = SimulationEngine(owner=_owner)
                sim.run_daily_simulation(date_str)
                results.append({"owner": _owner, "status": "ok"})
            except Exception as _e:
                results.append({"owner": _owner, "status": "error", "message": str(_e)})

        return jsonify({"status": "success", "date": date_str, "results": results})
    except Exception as e:
        import traceback
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500


@app.route('/api/admin/reset_requests', methods=['GET'])
def api_admin_reset_requests():
    """Yonetici: bekleyen sifirlama taleplerini listeler."""
    if not is_admin_owner():
        return jsonify({"status": "error", "message": "Bu endpoint yalnızca yönetici içindir."}), 403
    try:
        from services.trade_database import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("""SELECT r.id, r.owner_key, r.status, r.created_at, u.email, u.display_name
                     FROM reset_requests r LEFT JOIN app_users u ON u.owner_key = r.owner_key
                     WHERE r.status='PENDING' ORDER BY r.created_at ASC""")
        reqs = [dict(r) for r in c.fetchall()]
        conn.close()
        return jsonify({"status": "success", "requests": reqs})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/admin/reset_requests/decide', methods=['POST'])
def api_admin_reset_decide():
    """Yonetici: sifirlama talebini onaylar veya reddeder."""
    if not is_admin_owner():
        return jsonify({"status": "error", "message": "Bu endpoint yalnızca yönetici içindir."}), 403
    try:
        from services.trade_database import get_connection
        from services.live_trade_monitor import reset_portfolio
        data = request.get_json(force=True, silent=True) or {}
        req_id = data.get('id')
        action = (data.get('action') or '').lower()
        if not req_id or action not in ('approve', 'reject'):
            return jsonify({"status": "error", "message": "id ve action (approve/reject) gerekli"}), 400
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM reset_requests WHERE id=? AND status='PENDING'", (req_id,))
        row = c.fetchone()
        if row is None:
            conn.close()
            return jsonify({"status": "error", "message": "Talep bulunamadı (zaten işlenmiş olabilir)"}), 404
        owner = row["owner_key"]
        now = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M:%S")
        if action == 'approve':
            reset_portfolio(owner)
            c.execute("UPDATE reset_requests SET status='APPROVED', processed_at=? WHERE id=?", (now, req_id))
            msg = "Portföy sıfırlandı."
        else:
            c.execute("UPDATE reset_requests SET status='REJECTED', processed_at=? WHERE id=?", (now, req_id))
            msg = "Talep reddedildi."
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": msg})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

@app.route('/api/admin/set_cash', methods=['POST'])
def api_admin_set_cash():
    """Yonetici: herhangi bir hesabin bakiyesini dogrudan ayarlar.

    Iki sunucunun ayni pozu kapatmasi gibi gecmis hatalardan dolayi
    sismanmis bakiyeleri duzeltmek icindir. live_settings icindeki
    live_cash:<owner> degerini yazar.
    """
    if not is_admin_owner():
        return jsonify({"status": "error", "message": "Bu endpoint yalnızca yönetici içindir."}), 403
    try:
        from services.trade_database import get_connection
        from services.live_trade_monitor import _cash_key
        data = request.get_json(force=True, silent=True) or {}
        owner = (data.get('owner') or '').strip()
        cash = data.get('cash')
        if not owner or cash is None:
            return jsonify({"status": "error", "message": "owner ve cash zorunlu"}), 400
        try:
            cash = round(float(cash), 2)
        except (TypeError, ValueError):
            return jsonify({"status": "error", "message": "cash sayısal olmalı"}), 400
        if cash < 0 or cash > 10_000_000:
            return jsonify({"status": "error", "message": "cash aralık dışı (0 - 10.000.000)"}), 400

        # Hedef hesap gercekten var mi? (yanlis owner yazmayi engelle)
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT 1 FROM app_users WHERE owner_key=?", (owner,))
        if c.fetchone() is None:
            conn.close()
            return jsonify({"status": "error", "message": f"owner bulunamadi: {owner}"}), 404

        from services.live_trade_monitor import _set_setting
        _set_setting(_cash_key(owner), cash)
        conn.close()

        # Dogrulama icin geri oku
        from services.live_trade_monitor import _get_setting
        now_val = _get_setting(_cash_key(owner))
        return jsonify({"status": "success", "owner": owner, "cash": float(now_val)})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500

def _get_today_trade_stats():
    """Bugunun (Istanbul) Trade Log kayitlarindan portfoy istatistigi uretir.
    Tavan denetim arsivinden bagimsizdir; hesaba ozel gercek islemleri yansitir."""
    from services.trade_database import get_connection, IS_PG
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d")
    owner = get_owner_key()
    ph = "%s" if IS_PG else "?"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT symbol, entry_price, shares, pnl_val, pnl_pct, exit_time, exit_price FROM trades WHERE owner={ph} AND date_str={ph}",
            (owner, today)
        )
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    closed = [r for r in rows if r.get('exit_time')]
    pos = [r for r in closed if float(r.get('pnl_val') or 0) > 0]
    neg = [r for r in closed if float(r.get('pnl_val') or 0) < 0]
    invested = sum(float(r.get('entry_price') or 0) * int(r.get('shares') or 0) for r in closed)
    total_pnl = sum(float(r.get('pnl_val') or 0) for r in closed)
    avg_pos = sum(float(r.get('pnl_pct') or 0) for r in pos) / len(pos) if pos else 0.0
    avg_neg = sum(float(r.get('pnl_pct') or 0) for r in neg) / len(neg) if neg else 0.0
    trade_list = [{
        "symbol": r.get('symbol'),
        "entry_price": float(r.get('entry_price') or 0),
        "exit_price": float(r.get('exit_price') or 0),
        "shares": int(r.get('shares') or 0),
        "pnl_val": round(float(r.get('pnl_val') or 0), 2),
        "pnl_pct": round(float(r.get('pnl_pct') or 0), 2),
        "is_open": not bool(r.get('exit_time')),
    } for r in rows]
    return {
        "date": today,
        "open_count": len(rows) - len(closed),
        "closed_count": len(closed),
        "positive_count": len(pos),
        "negative_count": len(neg),
        "avg_positive_pct": round(avg_pos, 2),
        "avg_negative_pct": round(avg_neg, 2),
        "net_pnl": round(total_pnl, 2),
        "net_pct": round(total_pnl / invested * 100, 2) if invested > 0 else 0.0,
        "trades": trade_list,
    }


@app.route('/api/tavan_history', methods=['GET'])
def api_tavan_history():
    try:
        from services.tavan_tracker import TavanAuditTracker
        # Arka plan taraması henüz ilk denetim kaydını yazmadıysa, mevcut
        # gerçek dashboard cache'inden bir canlı snapshot oluştur. Böylece
        # Render yeniden başlatmalarında istatistik ekranı boş kalmaz.
        today_str = datetime.now().strftime("%Y-%m-%d")
        audits = TavanAuditTracker.load_all_audits()

        # 1) Bugunun kaydi yoksa veya items bos ise: gercek kaynaktan
        #    (signals + market_data tablolari) geri yukle. record_snapshot
        #    filtresi v8/metrik verisi bosken tum adaylari eleyip bos kayit
        #    biraktigi icin gunler bos kalmisti.
        today_entry = audits.get(today_str) or {}
        if not today_entry.get("items"):
            bf = TavanAuditTracker.backfill_from_db(today_str)
            if not bf:
                # Sinyal kaydi da yoksa mevcut cache'ten snapshot dene (eski davranis)
                cached_candidates = GLOBAL_DASHBOARD_CACHE.get("tavan_adaylari", [])
                cached_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
                if cached_stats:
                    TavanAuditTracker.record_snapshot(
                        cached_candidates,
                        all_symbols_stats=cached_stats,
                        date_str=today_str,
                    )
                    TavanAuditTracker.update_daily_progress(
                        cached_stats,
                        date_str=today_str,
                    )

        # 2) Son 7 gunde items bos kalan gunleri de geri yukle (arsiv tamamlama)
        try:
            for i in range(1, 8):
                from datetime import timedelta
                d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                day_entry = audits.get(d)
                if day_entry is not None and not day_entry.get("items"):
                    TavanAuditTracker.backfill_from_db(d)
        except Exception as be:
            print(f"[tavan_history] arsiv geri yukleme hatasi: {be}")
        start_date = request.args.get('start_date', '2026-08-04')
        end_date = request.args.get('end_date')
        symbol_filter = request.args.get('symbol_filter')
        time_filter = request.args.get('time_filter')
        res = TavanAuditTracker.get_long_term_history(
            start_date=start_date,
            end_date=end_date,
            symbol_filter=symbol_filter,
            time_filter=time_filter
        )
        # Trade Log istatistikleri tavan arsivinden ayridir; UI bunlari
        # kâr/zarar kartlarinda ayri kaynaktan gosterir.
        try:
            res["trade_stats"] = _get_today_trade_stats()
        except Exception as te:
            print(f"[tavan_history] trade_stats hatasi: {te}")
            res["trade_stats"] = None
        return jsonify(sanitize_for_json(res))
    except Exception as e:
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"})

@app.route('/api/winrate_stats', methods=['GET'])
def api_winrate_stats():
    try:
        from services.win_rate_engine import WinRateEngine
        from services.statistics_engine import StatisticsEngine
        stats = WinRateEngine.get_performance_stats()
        trade_performance = StatisticsEngine.get_trade_performance(get_owner_key())
        return jsonify({
            "status": "success",
            "stats": sanitize_for_json(stats),
            "trade_performance": sanitize_for_json(trade_performance)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/tavan_tracker', methods=['GET'])
def api_tavan_tracker():
    try:
        from services.tavan_tracker import TavanAuditTracker
        date_str = request.args.get('date')
        # Secili gun items bos ise sinyal/market_data kaynakli geri yukleme dene
        try:
            target = date_str or datetime.now().strftime("%Y-%m-%d")
            audits = TavanAuditTracker.load_all_audits()
            if not (audits.get(target) or {}).get("items"):
                TavanAuditTracker.backfill_from_db(target)
        except Exception as bfe:
            print(f"[tavan_tracker] backfill hatasi: {bfe}")
        res = TavanAuditTracker.get_audit_report(date_str)
        return jsonify(sanitize_for_json(res))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/simulation/daily_pnl', methods=['GET'])
def api_simulation_daily_pnl():
    try:
        from services.trade_database import get_connection
        import sqlite3
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            owner = get_owner_key()
            
            # Fetch daily equity log (hesaba ozel, tum gecmis aylar dahil)
            c.execute("SELECT * FROM equity_log WHERE owner=? ORDER BY date_str ASC", (owner,))
            equity_rows = c.fetchall()
            equity_curve = [dict(row) for row in equity_rows]
            if not equity_curve:
                from datetime import datetime
                equity_curve = [{"date_str": datetime.now().strftime("%Y-%m-%d"), "start_equity": 100000.0, "end_equity": 100000.0, "total_pnl": 0.0}]

            # Fetch all retained trades for this account, open and closed.
            c.execute("SELECT * FROM trades WHERE owner=? ORDER BY date_str DESC, entry_time DESC", (owner,))
            trade_rows = c.fetchall()
            trades = [dict(row) for row in trade_rows]
            if not trades:
                c.execute("SELECT * FROM trades ORDER BY date_str DESC, entry_time DESC LIMIT 500")
                trade_rows = c.fetchall()
                if trade_rows:
                    trades = [dict(row) for row in trade_rows]
                if not equity_curve or (len(equity_curve) == 1 and float(equity_curve[0].get("daily_pnl") or equity_curve[0].get("total_pnl") or 0.0) == 0.0):
                    c.execute("SELECT * FROM equity_log ORDER BY date_str ASC")
                    eq_fb = c.fetchall()
                    if eq_fb:
                        equity_curve = [dict(row) for row in eq_fb]

            # Bakiye eğrisi için gerçekleşen işlem defteri kaynak kabul edilir.
            # Eski equity_log satırlarında kuruş yuvarlama/önceki yarış durumundan
            # kalan farklar olabilir; seansları işlem kayıtlarından tekrar uzlaştır.
            realized_by_date = {}
            for trade in trades:
                trade_date = str(trade.get("date_str") or "")
                if not trade_date:
                    continue
                bucket = realized_by_date.setdefault(trade_date, {"pnl": 0.0, "count": 0, "wins": 0})
                bucket["count"] += 1
                realized = float(trade.get("realized_pnl") or 0)
                bucket["pnl"] += realized
                if trade.get("exit_time") and realized > 0:
                    bucket["wins"] += 1
            if not equity_rows:
                if realized_by_date:
                    equity_curve = []
                    running_balance = 100000.0
                    for trade_date in sorted(realized_by_date):
                        totals = realized_by_date[trade_date]
                        start = running_balance
                        running_balance += totals["pnl"]
                        equity_curve.append({
                            "date_str": trade_date,
                            "start_equity": start,
                            "end_equity": running_balance,
                            "daily_pnl": totals["pnl"],
                            "total_trades": totals["count"],
                            "win_trades": totals["wins"],
                        })
            else:
                known_dates = {str(row.get("date_str") or "") for row in equity_curve}
                for trade_date in realized_by_date:
                    if trade_date not in known_dates:
                        equity_curve.append({"date_str": trade_date, "start_equity": 100000.0, "end_equity": 100000.0, "daily_pnl": 0.0})
                equity_curve.sort(key=lambda row: str(row.get("date_str") or ""))
            previous_end = None
            for row in equity_curve:
                day = str(row.get("date_str") or "")
                start = previous_end if previous_end is not None else float(row.get("start_equity") or 100000.0)
                totals = realized_by_date.get(day)
                if totals is not None:
                    daily_pnl = totals["pnl"]
                    row["total_trades"] = totals["count"]
                    row["win_trades"] = totals["wins"]
                else:
                    daily_pnl = float(row.get("daily_pnl") or 0)
                row["start_equity"] = start
                row["daily_pnl"] = daily_pnl
                row["end_equity"] = start + daily_pnl
                previous_end = row["end_equity"]
            
            # KÜMÜLATİF ASLA SIFIRLANMAYAN YEKÜN HESABI (TÜM AYLAR VE ANLIK AÇIK POZİSYONLAR DAHİL)
            c.execute("SELECT COUNT(*), COALESCE(SUM(pnl_val), 0.0), SUM(CASE WHEN pnl_val > 0 THEN 1 ELSE 0 END) FROM trades WHERE owner=? AND exit_time IS NOT NULL", (owner,))
            tot_row = c.fetchone()
            all_time_closed_trades = int(tot_row[0] or 0)
            all_time_closed_pnl = round(float(tot_row[1] or 0.0), 2)
            all_time_wins = int(tot_row[2] or 0)
            
            try:
                c.execute("SELECT COALESCE(SUM(pnl_val), 0.0), COUNT(*) FROM live_positions WHERE owner=? AND pnl_val IS NOT NULL", (owner,))
                lp_row = c.fetchone()
                open_pnl = round(float(lp_row[0] or 0.0), 2) if lp_row else 0.0
                open_count = int(lp_row[1] or 0) if lp_row else 0
            except Exception:
                open_pnl = 0.0
                open_count = 0
            
            c.execute('''
                SELECT SUBSTR(entry_time, 1, 7) as month_key, COUNT(*) as cnt, COALESCE(SUM(pnl_val), 0.0) as pnl
                FROM trades
                WHERE owner=? AND exit_time IS NOT NULL
                GROUP BY month_key
                ORDER BY month_key ASC
            ''', (owner,))
            monthly_breakdown = [
                {"month": r["month_key"], "trades": r["cnt"], "pnl": round(float(r["pnl"] or 0.0), 2)}
                for r in c.fetchall()
            ]
            
            base_starting_capital = 100000.0
            if equity_curve and equity_curve[0].get("start_equity"):
                base_starting_capital = float(equity_curve[0]["start_equity"])
                
            latest_logged_equity = float(equity_curve[-1]["end_equity"]) if equity_curve else base_starting_capital
            cumulative_equity = round(latest_logged_equity + open_pnl, 2)
            cumulative_net_pnl = round(cumulative_equity - base_starting_capital, 2)
            cumulative_return_pct = round((cumulative_net_pnl / base_starting_capital) * 100, 2)
            
            # HAFTALIK %6 HEDEF VE BAŞARI HESABI (Pazartesi'den Cuma'ya)
            from datetime import datetime as _dt_cls, timedelta as _td_cls
            now_dt = _dt_cls.now()
            monday_str = (now_dt - _td_cls(days=now_dt.weekday())).strftime("%Y-%m-%d")
            c.execute('''
                SELECT COUNT(*), COALESCE(SUM(pnl_val), 0.0), SUM(CASE WHEN pnl_val > 0 THEN 1 ELSE 0 END)
                FROM trades
                WHERE owner=? AND exit_time IS NOT NULL AND date_str >= ?
            ''', (owner, monday_str))
            wk_row = c.fetchone()
            wk_trades = int(wk_row[0] or 0)
            wk_closed_pnl = round(float(wk_row[1] or 0.0), 2)
            wk_wins = int(wk_row[2] or 0)
            wk_win_rate = round((wk_wins / wk_trades * 100), 1) if wk_trades > 0 else 0.0
            wk_total_pnl = round(wk_closed_pnl + open_pnl, 2)
            wk_return_pct = round((wk_total_pnl / base_starting_capital) * 100, 2)
            weekly_summary = {
                "monday_date": monday_str,
                "target_pct": 6.0,
                "current_return_pct": wk_return_pct,
                "net_pnl_tl": wk_total_pnl,
                "trades_count": wk_trades,
                "wins_count": wk_wins,
                "win_rate": wk_win_rate,
                "target_achieved": wk_return_pct >= 6.0,
                "progress_pct": min(100.0, max(0.0, round((wk_return_pct / 6.0) * 100, 1))) if wk_return_pct > 0 else 0.0,
                "status": "HEDEF TAMAMLANDI 🎯" if wk_return_pct >= 6.0 else "HEDEF YOLUNDA 🚀"
            }

            from services.statistics_engine import StatisticsEngine
            performance = StatisticsEngine.get_trade_performance(owner)
            # Haftalık hedef: takvim haftasının simülasyon bakiyesi.
            # /api/v8/weekly ile aynı hafta tanımı kullanılır; iki ekran
            # farklı yüzde göstermesin.
            from datetime import datetime, timedelta
            _now_local = datetime.now(ZoneInfo("Europe/Istanbul"))
            _monday = (_now_local.date() - timedelta(days=_now_local.weekday())).strftime("%Y-%m-%d")
            weekly_rows = [r for r in equity_curve if str(r.get("date_str", "")) >= _monday]
            weekly_start = float(weekly_rows[0].get('start_equity') or 0) if weekly_rows else 0.0
            weekly_end = float(weekly_rows[-1].get('end_equity') or weekly_start) if weekly_rows else weekly_start
            weekly_pct = ((weekly_end - weekly_start) / weekly_start * 100.0) if weekly_start > 0 else 0.0
            target_pct = 6.0
            # ORTAK HAFTALIK KILIT (playbook): rejime gore zarar limiti ve
            # giris durdurma durumu panoda gosterilir; V8 ve simülasyon ayni
            # karari kullanir.
            weekly_guard = {}
            try:
                from v8_engine.playbook import get_weekly_guard
                _regime = (GLOBAL_DASHBOARD_CACHE.get("v8_market_regime") or {}).get("regime", "NEUTRAL")
                weekly_guard = get_weekly_guard(
                    weekly_end - weekly_start, weekly_start, _regime,
                )
                weekly_guard.pop("regime", None)
            except Exception:
                pass
            return jsonify({
                "status": "success",
                "equity_curve": sanitize_for_json(equity_curve),
                "trades": sanitize_for_json(trades),
                "performance": sanitize_for_json(performance),
                "weekly_summary": sanitize_for_json(weekly_summary),
                "weekly_target": {
                    "target_pct": target_pct,
                    "actual_pct": round(weekly_pct, 2),
                    "gap_pct": round(target_pct - weekly_pct, 2),
                    "reached": weekly_pct >= target_pct,
                    "sessions": len(weekly_rows),
                    "label": "Haftalık %6 hedef takibi (garanti değildir)",
                    "guard": sanitize_for_json(weekly_guard),
                }
            })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/legal/status', methods=['GET'])
def api_legal_status():
    """Yasal sorumluluk onayi durumu (hesap bazli, kalici)."""
    try:
        owner = get_owner_key()
        from services.trade_database import get_connection, IS_PG
        ph = "%s" if IS_PG else "?"
        val = None
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT value FROM live_settings WHERE key = {ph}", (f"legal_accepted:{owner}",))
            row = cur.fetchone()
            if row and row["value"]:
                val = row["value"]
        return jsonify({"status": "success", "accepted": bool(val), "accepted_at": val})
    except Exception as e:
        return jsonify({"status": "error", "accepted": False, "message": str(e)})

@app.route('/api/legal/accept', methods=['POST'])
def api_legal_accept():
    """Kullanicinin tek seferlik yasal onayini kalici olarak kaydeder."""
    try:
        owner = get_owner_key()
        from services.trade_database import get_connection, IS_PG
        ph = "%s" if IS_PG else "?"
        ts = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M:%S")
        key = f"legal_accepted:{owner}"
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT key FROM live_settings WHERE key = {ph}", (key,))
            exists = cur.fetchone()
            if exists:
                cur.execute(f"UPDATE live_settings SET value = {ph} WHERE key = {ph}", (ts, key))
            else:
                cur.execute(f"INSERT INTO live_settings (key, value) VALUES ({ph}, {ph})", (key, ts))
            conn.commit()
        return jsonify({"status": "success", "accepted": True, "accepted_at": ts})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/telegram/settings', methods=['GET', 'POST'])
def api_telegram_settings():
    """Telegram bot ayarlari: durum sorgulama (GET) ve kalici kayit (POST).
    Ayarlar veritabanina kaydedilir; deploy'lar arasi korunur."""
    try:
        from services.telegram_bot import get_telegram_credentials, set_telegram_credentials
        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
            t = (data.get('token') or '').strip()
            c = (data.get('chat_id') or '').strip()
            if not t or not c:
                return jsonify({"status": "error", "message": "Bot token ve Chat ID zorunludur."}), 400
            ok = set_telegram_credentials(t, c)
            if not ok:
                return jsonify({"status": "error", "message": "Ayarlar kaydedilemedi."}), 500
        bt, cid = get_telegram_credentials(force=True)
        return jsonify({
            "status": "success",
            "configured": bool(bt and cid),
            "chat_id_masked": ('•••' + cid[-4:]) if cid else None,
        })
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500


@app.route('/api/telegram/test', methods=['POST'])
def api_telegram_test():
    """Telegram baglanti testi: kayitli ayarlarla test mesaji gonderir."""
    try:
        from services.telegram_bot import send_telegram_message, get_telegram_credentials
        bt, cid = get_telegram_credentials(force=True)
        if not bt or not cid:
            return jsonify({"status": "error", "message": "Telegram ayarlari eksik. Once token ve chat ID kaydedin."}), 400
        ok = send_telegram_message(
            "✅ <b>VarantRadar Pro</b> — Telegram baglanti testi basarili!\n"
            "🤖 Simulasyon AL/SAT bildirimleri bu kanala gelecek.",
            force=True
        )
        if ok:
            return jsonify({"status": "success", "message": "Test mesaji gonderildi. Telegram'ı kontrol edin."})
        return jsonify({"status": "error", "message": "Gonderim basarisiz. Token/Chat ID'yi ve botun sohbeti baslattigini kontrol edin."}), 500
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500


@app.route('/api/simulation/send_telegram', methods=['POST'])
def api_simulation_send_telegram():
    """Tekil özel format üretmez; aynı tek-gün özeti ve dedup akışını kullanır."""
    try:
        data = request.get_json(silent=True) or {}
        date_str = data.get('date')
        if not date_str:
            return jsonify({"status": "error", "message": "Tarih gerekli."}), 400
        owner = get_owner_key()
        from services.trade_database import get_connection
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT start_equity FROM equity_log WHERE owner=? AND date_str=?", (owner, date_str))
            equity = cur.fetchone()
            if not equity:
                return jsonify({"status": "error", "message": "Bu tarihe ait simülasyon özeti yok."}), 404
            base = float(equity['start_equity'] or 0)
            cur.execute("SELECT COUNT(*) c, COALESCE(SUM(realized_pnl),0) p FROM trades WHERE owner=? AND date_str=? AND exit_time IS NOT NULL", (owner, date_str))
            totals = cur.fetchone()
        profit = float(totals['p'] or 0)
        count = int(totals['c'] or 0)
        pct = profit / base * 100 if base > 0 else 0.0
        from services.telegram_bot import send_simulation_report
        if send_simulation_report(count, profit, pct, date_str, owner):
            return jsonify({"status": "success", "message": "Standart simülasyon gün özeti gönderildi (aynı gün tekrarı engellenir)."})
        return jsonify({"status": "error", "message": "Telegram gönderilemedi; ayarları kontrol edin."}), 503
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


import time
XU100_CACHE = {"change": 0.0, "last_updated": 0}

_xu100_refreshing = False
def get_xu100_change():
    """5 dk cache. Tazeleme arka planda yapilir; dashboard senkron beklemez."""
    global XU100_CACHE, _xu100_refreshing
    now = time.time()
    if now - XU100_CACHE['last_updated'] > 300 and not _xu100_refreshing:
        _xu100_refreshing = True

        def _refresh():
            global XU100_CACHE, _xu100_refreshing
            try:
                import yfinance as yf
                hist = yf.Ticker('XU100.IS').history(period='5d')
                if len(hist) >= 2:
                    c1 = hist['Close'].iloc[-2]
                    c2 = hist['Close'].iloc[-1]
                    chg = ((c2 - c1) / c1) * 100
                    XU100_CACHE['change'] = chg
                    XU100_CACHE['last_updated'] = time.time()
            except Exception:
                pass
            finally:
                _xu100_refreshing = False

        threading.Thread(target=_refresh, daemon=True).start()
    return XU100_CACHE['change']




@app.route('/api/v8/learning/outcomes', methods=['GET'])
def api_v8_learning_outcomes():
    try:
        from v8_engine.database import V8Database
        try:
            V8Database.init_db()
        except Exception:
            pass
        conn = V8Database.get_connection()
        cursor = conn.cursor()
        
        cohort_filter = request.args.get('cohort', 'all').lower()
        
        # Sinyalleri, kohort (engine_version) bilgisi ve sonuclariyla JOIN ile getir
        query = '''
            SELECT s.signal_id, s.symbol, s.timestamp, s.entry_price, s.score, s.status, s.market_regime,
                   COALESCE(s.engine_version, 'LEGACY') as engine_version,
                   o.t_3m_price, o.t_5m_price, o.t_10m_price, o.t_15m_price,
                   o.t_30m_price, o.t_60m_price, o.t_120m_price, o.t_240m_price,
                   o.t_eod_price, o.t_1d_price,
                   o.max_favorable_excursion as mfe, o.max_adverse_excursion as mae, o.final_result
            FROM v8_signals s
            LEFT JOIN v8_outcomes o ON s.signal_id = o.signal_id
            ORDER BY s.timestamp DESC
            LIMIT 50
        '''
        cursor.execute(query)
        rows = cursor.fetchall()
        
        outcomes = []
        verified_outcomes = []
        # KOHORT ISTATISTIKLERI: yeni motor (V8_PRO) ile eski motor (LEGACY)
        # kayitlari ayri raporlanir ki eski motorun dusuk kazanma orani yeni
        # motorun gercek performansini kirletmesin.
        cohorts = {}
        for r in rows:
            engine_version = r["engine_version"] or "LEGACY"
            # MAE koruması: bazı dış/legacy kayıtlarındaki ham MAE değerleri
            # fiyat pencereleriyle matematiksel olarak uyuşmuyor (ör. -%36).
            # Ekranda gerçek gözlenen pencerelerden hesaplanan değeri kullan.
            entry = float(r["entry_price"] or 0)
            observed = []
            if entry > 0:
                for key in (
                    "t_3m_price", "t_5m_price", "t_10m_price", "t_15m_price",
                    "t_30m_price", "t_60m_price", "t_120m_price", "t_240m_price",
                    "t_eod_price", "t_1d_price",
                ):
                    price = r[key]
                    if price is not None:
                        try:
                            observed.append((float(price) - entry) / entry * 100.0)
                        except (TypeError, ValueError):
                            pass
            raw_mfe = float(r["mfe"] or 0)
            observed_mfe = max(0.0, max(observed)) if observed else raw_mfe
            raw_mae = float(r["mae"] or 0)
            observed_mae = min(0.0, min(observed)) if observed else raw_mae
            # Ham eski değerleri yalnızca gözlenen pencerelerle uyuşuyorsa geçerli say.
            mfe_valid = abs(raw_mfe - observed_mfe) <= 0.25 if observed else 0.0 <= raw_mfe <= 15.0
            mae_valid = abs(raw_mae - observed_mae) <= 0.25 if observed else abs(raw_mae) <= 15.0
            display_mfe = observed_mfe if observed else max(0.0, min(15.0, raw_mfe))
            display_mae = observed_mae if observed else max(-15.0, min(0.0, raw_mae))
            item = {
                "signal_id": r["signal_id"],
                "symbol": r["symbol"],
                "timestamp": r["timestamp"],
                "entry_price": r["entry_price"],
                "score": r["score"],
                "status": r["status"],
                "market_regime": r["market_regime"],
                "engine_version": engine_version,
                "t_3m_price": r["t_3m_price"],
                "t_5m_price": r["t_5m_price"],
                "t_10m_price": r["t_10m_price"],
                "t_15m_price": r["t_15m_price"],
                "t_30m_price": r["t_30m_price"],
                "t_60m_price": r["t_60m_price"],
                "t_120m_price": r["t_120m_price"],
                "t_240m_price": r["t_240m_price"],
                "t_eod_price": r["t_eod_price"],
                "t_1d_price": r["t_1d_price"],
                "mfe": round(display_mfe, 4),
                "mfe_raw": raw_mfe,
                "mfe_valid": mfe_valid,
                "mae": round(display_mae, 4),
                "mae_raw": raw_mae,
                "mae_valid": mae_valid,
                "final_result": r["final_result"]
            }
            outcomes.append(item)
            if engine_version == "V8_PRO":
                verified_outcomes.append(item)
            # Kohort sayaci: WIN / LOSS / kapansmamin sayisini tut.
            c = cohorts.setdefault(engine_version, {"total": 0, "win": 0, "loss": 0, "decided": 0})
            c["total"] += 1
            fr = str(r["final_result"] or "")
            if fr in ("WIN", "LOSS"):
                c["decided"] += 1
                if fr == "WIN":
                    c["win"] += 1
                else:
                    c["loss"] += 1
        for name, c in cohorts.items():
            c["win_rate"] = round(100.0 * c["win"] / c["decided"], 1) if c["decided"] else 0.0

        conn.close()
        return jsonify({
            "status": "success",
            "data": outcomes,
            "verified_data": verified_outcomes,
            "verified_engine": "V8_PRO",
            "cohorts": cohorts,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/v8/radar/share-signal', methods=['POST'])
def api_v8_radar_share_signal():
    """Kartta gorunen tek bir V8 giris sinyalini islem planiyle Telegram'a gonderir."""
    try:
        payload = request.get_json(silent=True) or {}
        symbol = str(payload.get("symbol") or "").strip().upper()
        if not symbol:
            return jsonify({"status": "error", "message": "Hisse kodu eksik."}), 400

        all_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
        data = all_stats.get(symbol)
        if not data:
            return jsonify({"status": "error", "message": f"{symbol} için güncel tarama verisi bulunamadı."}), 404

        bo = data.get("v8_breakout") or {}
        metrics = bo.get("metrics") or {}
        entry = float(data.get("Price") or data.get("Daily_Close") or 0)
        if entry <= 0:
            return jsonify({"status": "error", "message": f"{symbol} için fiyat verisi yok."}), 404

        try:
            atr_pct = float(metrics.get("atr_pct") or 0)
        except (TypeError, ValueError):
            atr_pct = 0.0
        if atr_pct > 0:
            stop_dist = max(2.0, min(8.0, atr_pct * 1.5))
            tgt1_dist = max(2.0, min(10.0, atr_pct * 1.5))
            tgt2_dist = max(3.0, min(15.0, atr_pct * 2.5))
        else:
            stop_dist, tgt1_dist, tgt2_dist = 5.0, 3.0, 5.0

        regime_raw = GLOBAL_DASHBOARD_CACHE.get("v8_market_regime", {}).get("regime", "")
        V8_REGIME_TR = {
            "STRONG_BULL": "GÜÇLÜ BOĞA (RALLİ)", "BULL": "BOĞA (YÜKSELİŞ TRENDİ)",
            "NEUTRAL": "NÖTR (YATAY / DENGE)", "BEAR": "AYI (DÜŞÜŞ BASKISI)",
            "STRONG_BEAR": "GÜÇLÜ AYI (SERT SATIŞ)",
        }
        cache_ts = GLOBAL_DASHBOARD_CACHE.get("cache_timestamp")
        try:
            scan_time = datetime.fromtimestamp(float(cache_ts)).strftime("%d.%m.%Y %H:%M") if cache_ts else ""
        except (TypeError, ValueError, OSError):
            scan_time = ""

        signal = {
            "symbol": symbol,
            "entry_price": entry,
            "stop_price": entry * (1 - stop_dist / 100.0),
            "target1": entry * (1 + tgt1_dist / 100.0),
            "target2": entry * (1 + tgt2_dist / 100.0),
            "breakout_score": bo.get("breakout_score") or (data.get("v8_discovery") or {}).get("preparation_score", 0),
            "fakeout_risk": bo.get("fakeout_risk", 0),
            "reason": ((data.get("v8_execution") or {}).get("reasons") or [""])[0],
            "market_regime": V8_REGIME_TR.get(regime_raw, regime_raw),
            "scan_time": scan_time,
        }

        from services.telegram_bot import send_v8_entry_signal
        if not send_v8_entry_signal(signal):
            return jsonify({
                "status": "error",
                "message": "Telegram gönderilemedi. Bot tokeni ve kanal Chat ID ayarlarını kontrol edin."
            }), 503
        return jsonify({"status": "success", "message": f"{symbol} işlem sinyali Telegram'a gönderildi."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/v8/learning/share-profits', methods=['POST'])
def api_v8_learning_share_profits():
    """V8'in kapanmış kârlı sonuçlarını yapılandırılmış Telegram kanalına yollar."""
    try:
        from v8_engine.database import V8Database
        conn = V8Database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.symbol, s.entry_price, s.timestamp,
                   COALESCE(o.t_1d_price, o.t_eod_price, o.t_240m_price,
                            o.t_120m_price, o.t_60m_price, o.t_30m_price,
                            o.t_15m_price, o.t_10m_price, o.t_5m_price,
                            o.t_3m_price) AS exit_price,
                   o.max_favorable_excursion AS mfe
            FROM v8_signals s
            JOIN v8_outcomes o ON s.signal_id = o.signal_id
            WHERE s.status = 'CLOSED' AND o.final_result = 'WIN'
            ORDER BY s.timestamp DESC
            LIMIT 15
        ''')
        rows = cursor.fetchall()
        profits = []
        for row in rows:
            entry = float(row["entry_price"] or 0)
            exit_price = float(row["exit_price"] or 0)
            if entry <= 0 or exit_price <= 0:
                continue
            profits.append({
                "symbol": row["symbol"],
                "entry_price": entry,
                "exit_price": exit_price,
                "profit_pct": ((exit_price - entry) / entry) * 100,
                "mfe": float(row["mfe"] or 0),
            })
        conn.close()

        if not profits:
            return jsonify({"status": "error", "message": "Paylaşılacak kapanmış kârlı V8 işlemi yok."}), 404

        from services.telegram_bot import send_v8_profit_report
        if not send_v8_profit_report(profits):
            return jsonify({
                "status": "error",
                "message": "Telegram gönderilemedi. Bot tokeni ve kanal Chat ID ayarlarını kontrol edin."
            }), 503
        return jsonify({"status": "success", "count": len(profits), "message": "V8 kârları Telegram kanalına gönderildi."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def _stats_rel_vol(data: dict) -> float:
    """Gunluk istatistikten gercek goreceli hacim uretir (1.0x donmasin)."""
    try:
        vm = data.get("Vol_Multiplier") or data.get("Volume_Ratio")
        if vm:
            return float(vm)
        v = float(data.get("Volume") or 0)
        vs = float(data.get("Vol_SMA10") or 0)
        if v > 0 and vs > 0:
            return round(v / vs, 2)
        # Eski cache'te Vol_SMA10 yoksa V8 discovery motorunun gercek
        # goreceli hacmine dus (1.0x donuk deger gosterme).
        disc_rv = ((data.get("v8_discovery") or {}).get("metrics") or {}).get("relative_volume")
        if disc_rv:
            return round(float(disc_rv), 2)
    except Exception:
        pass
    return 1.0

_V8_TG_SENT = set()

# ==== V8 ZAMANLANMIS TELEGRAM RAPORLARI ====
# Sabah 09:40 pusula bulteni + aksam 18:20 gun sonu kar raporu.
# Gunde bir kez; claim_telegram_alert ile mukerrer gönderim engellenir.
_V8_SCHED_SENT = set()

def _v8_scheduled_reports(now=None):
    try:
        from datetime import datetime as _dt_sched, timezone, timedelta as _td_sched
        from services.telegram_bot import (
            claim_telegram_alert, send_simulation_session_opening,
            send_simulation_report,
        )
        if now is None:
            now = _dt_sched.now(ZoneInfo("Europe/Istanbul"))
        day_key = now.strftime("%Y-%m-%d")

        # Seans açılışı (10:00-10:05, günde bir kez); yalnızca kısa sistem durumu.
        if now.hour == 10 and 0 <= now.minute <= 5:
            sk = f"SIM_SESSION_OPEN_{day_key}"
            if sk not in _V8_SCHED_SENT:
                if claim_telegram_alert(sk):
                    _V8_SCHED_SENT.add(sk)
                    try:
                        ok = send_simulation_session_opening(day_key)
                        print(f"[SIM-SCHED] Seans açılışı: {'gönderildi' if ok else 'gönderilemedi'}")
                    except Exception as opening_err:
                        print(f"[SIM-SCHED] Seans açılışı hatası: {opening_err}")
                else:
                    _V8_SCHED_SENT.add(sk)

        # Gün sonu simülasyon özeti (18:20'den sonra, günde bir kez).
        if (now.hour == 18 and now.minute >= 20) or now.hour >= 19:
            ek = f"EVENING_REPORT_{day_key}"
            if ek not in _V8_SCHED_SENT:
                if claim_telegram_alert(ek):
                    _V8_SCHED_SENT.add(ek)
                    try:
                        from services.trade_database import get_connection as _tg_conn
                        owner = os.environ.get("ADMIN_OWNER", "local:nebioglur")
                        conn = _tg_conn()
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT COUNT(CASE WHEN exit_time IS NOT NULL THEN 1 END) c, "
                            "COALESCE(SUM(realized_pnl),0) p FROM trades "
                            "WHERE date_str=? AND owner=?",
                            (day_key, owner),
                        )
                        row = cur.fetchone()
                        cur.execute(
                            "SELECT start_equity FROM equity_log WHERE owner=? AND date_str=?",
                            (owner, day_key),
                        )
                        eq = cur.fetchone()
                        conn.close()
                        t_count = int(row["c"]) if row else 0
                        profit = float(row["p"]) if row else 0.0
                        base = float(eq["start_equity"]) if eq and eq["start_equity"] else 100000.0
                        ret_pct = (profit / base * 100.0) if base > 0 else 0.0
                        ok = send_simulation_report(t_count, profit, ret_pct, day_key, owner)
                        print(f"[V8-SCHED] Aksam raporu: {'gonderildi' if ok else 'gonderilemedi (config?)'} | {t_count} islem, {profit:+.0f} TL ({ret_pct:+.2f}%)")
                    except Exception as ev_e:
                        print(f"[V8-SCHED] Aksam raporu hatasi: {ev_e}")
                else:
                    _V8_SCHED_SENT.add(ek)
        if len(_V8_SCHED_SENT) > 100:
            _V8_SCHED_SENT.clear()
    except Exception as e:
        print(f"[V8-SCHED] zamanlayici hatasi: {e}")


# ==== V8 GIRIS TEYIT MOTORU (T+3 dakika kurali) ====
# Canli istatistik: sinyal geldikten sonraki ilk 3 dakikada -%0.5 altina
# dusan girislerin kazanma orani %0 (0/17). Bu yuzden her ENTER sinyali
# once 3 dakika gozlemlenir; fiyat sinyal fiyatinin uzerinde kalmazsa
# giris reddedilir ve ayni gun bir daha acilmaz.
_V8_ENTRY_CONFIRM = {}

def _v8_regime_locked() -> bool:
    """AYI / GUCCLU AYI rejiminde kirilim girisleri tamamen kilitlidir."""
    regime_raw = (GLOBAL_DASHBOARD_CACHE.get("v8_market_regime") or {}).get("regime", "")
    return regime_raw in ("BEAR", "STRONG_BEAR")

_V8_SECTOR_STRENGTH_CACHE = {"ts": 0.0, "map": {}}

def _v8_sector_strength_map() -> dict:
    """Sektor -> dalga gucu haritasi (60 sn cache ile)."""
    import time as _time
    now = _time.time()
    if now - _V8_SECTOR_STRENGTH_CACHE["ts"] < 60 and _V8_SECTOR_STRENGTH_CACHE["map"]:
        return _V8_SECTOR_STRENGTH_CACHE["map"]
    try:
        from v8_engine.playbook import sector_pulse
        pulse = sector_pulse(GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {}), top_n=15)
        smap = {p["sector"]: p["strength"] for p in pulse}
    except Exception:
        smap = {}
    _V8_SECTOR_STRENGTH_CACHE.update({"ts": now, "map": smap})
    return smap

def _v8_defense_mode_check(row: dict, sym: str, data: dict) -> bool:
    """SAVUNMA MODU istisnasi: SADECE AYI (BEAR) rejiminde, endekse karsi
    yesil kalan ve dalgasi yukselen (+25+) sektordeki A kalite hisse icin
    tek giris izni. GUCCLU AYI'da istisna yoktur."""
    regime_raw = (GLOBAL_DASHBOARD_CACHE.get("v8_market_regime") or {}).get("regime", "")
    if regime_raw != "BEAR":
        return False  # STRONG_BEAR ve digerlerinde istisna yok
    try:
        chg = float(row.get("change_pct") or data.get("Change_Pct") or 0)
    except (TypeError, ValueError):
        return False
    if not (0.5 <= chg <= 4.8):
        return False  # endekse karsi gercek yesil ayrilma olmali
    try:
        vol = float(data.get("Vol_Multiplier") or data.get("Volume_Ratio") or 0)
        if vol < 1.5:
            vol = float(_stats_rel_vol(data) or 0)
    except (TypeError, ValueError):
        vol = 0.0
    if vol < 1.5:
        return False  # sig hacim savunma islemine girmez
    price = float(data.get("Price") or data.get("Daily_Close") or 0)
    if price < 3:
        return False
    try:
        from services.detective_engine import SECTOR_OF
        base = str(sym).replace(".IS", "")
        sector = SECTOR_OF.get(base) or SECTOR_OF.get(str(sym))
    except Exception:
        return False
    if not sector:
        return False
    return _v8_sector_strength_map().get(sector, -100.0) >= 25.0

def _v8_entry_confirmation(sym: str, price):
    """ENTER sinyali icin T+3 dakika teyit degerlendirmesi.
    Donus: ("CONFIRMED"|"PENDING"|"REJECTED", mesaj)"""
    from datetime import datetime as _dt
    try:
        price = float(price or 0)
    except (TypeError, ValueError):
        return "REJECTED", "Fiyat okunamadı"
    if price <= 0:
        return "REJECTED", "Fiyat okunamadı"
    today = _dt.now().strftime("%Y-%m-%d")
    now = _dt.now().timestamp()
    key = (today, sym)
    rec = _V8_ENTRY_CONFIRM.get(key)
    if rec and rec.get("date") != today:
        rec = None
    if rec is None:
        _V8_ENTRY_CONFIRM[key] = {"date": today, "ts": now, "price": price,
                                  "state": "PENDING", "rejected_reason": ""}
        return "PENDING", "Sinyal alındı; 3 dakikalık teyit süresi başladı"
    state = rec.get("state")
    if state == "CONFIRMED":
        return "CONFIRMED", "3 dakika teyidi geçildi"
    if state == "REJECTED":
        return "REJECTED", rec.get("rejected_reason") or "Daha önce reddedildi"
    entry_price = float(rec.get("price") or 0)
    elapsed = now - float(rec.get("ts") or now)
    if price <= entry_price * 0.99:
        rec["state"] = "REJECTED"
        rec["rejected_reason"] = f"Sinyal sonrası fiyat hızla düştü (₺{entry_price:.2f} → ₺{price:.2f})"
        return "REJECTED", rec["rejected_reason"]
    if elapsed >= 180:
        if price >= entry_price * 0.995:
            rec["state"] = "CONFIRMED"
            return "CONFIRMED", "3 dakika teyidi geçildi (en fazla %0,5 geri çekilme)"
        rec["state"] = "REJECTED"
        rec["rejected_reason"] = f"İlk 3 dakikada sinyal fiyatının altında kaldı (₺{entry_price:.2f} → ₺{price:.2f})"
        return "REJECTED", rec["rejected_reason"]
    return "PENDING", f"Teyit süresi devam ediyor ({int(180 - elapsed)} sn)"

def _v8_a_class_gate(row: dict, sym: str, data: dict):
    """Kalite filtresi: gerçek kırılımda temel fiyat/hacim koşullarını uygular.
    Saatlik akış ve sektör verisi eksikse tek başına ret nedeni yapılmaz;
    açık satış akışı ise reddedilir. Boğa/ayı rejim ve KAP kilitleri ayrıca işler."""
    reasons = []
    try:
        chg = float(row.get("change_pct") or data.get("Change_Pct") or 0)
    except (TypeError, ValueError):
        chg = 0.0
    if chg >= 9.2:
        reasons.append(f"Hisse tavana kilitli/çok yakın (+{chg:+.1f}%; tavan riski)")
    elif chg < -2.5:
        reasons.append(f"Hisse belirgin ekside ({chg:+.1f}%)")

    try:
        vol = float(data.get("Vol_Multiplier") or data.get("Volume_Ratio") or _stats_rel_vol(data) or 0)
    except (TypeError, ValueError):
        vol = 0.0
    if vol < 0.8:
        reasons.append(f"Hacim ortalamanın altında ({vol:.1f}x; en az 0.8x gerekli)")

    intra = data.get("intraday_strength") or {}
    flow = str(intra.get("hourly_flow") or "").strip().casefold()
    if flow in ("satılıyor", "satiliyor"):
        reasons.append("Saatlik akışta belirgin satış var")

    return (len(reasons) == 0, reasons)

def _v8_gate_enter_row(row: dict, sym: str, data: dict) -> dict:
    """ENTER satirlarina rejim kilidi + KAP filtresi + T+3 teyit filtresi
    uygular. Reddedilen ya da bekleyen sinyaller WAIT_CONFIRMATION'a dusurulur."""
    if (row.get("entry_status") or "").upper() != "ENTER":
        return row
    if _v8_regime_locked():
        # SAVUNMA MODU istisnasi: AYI gununde sektor dalgasi yukselen,
        # endekse karsi yesil kalan tek hisse girebilir (gunde max 1).
        if _v8_defense_mode_check(row, sym, data):
            row["defense_mode"] = True
        else:
            row["entry_status"] = "WAIT_CONFIRMATION"
            row["regime_locked"] = True
            row["entry_reasons"] = ["Piyasa AYI rejiminde; kırılım girişleri kilitli"] + list(row.get("entry_reasons") or [])
            return row
    # KAP HABER FILTRESI: son 24 saatte onemli olay duyurusu varsa girme.
    try:
        from services.kap_news import check_symbol as _kap_check
        kap = _kap_check(sym)
        row["kap_ok"] = kap.get("kap_ok", False)
        row["kap_count"] = kap.get("count", 0)
        if kap.get("blocked"):
            row["entry_status"] = "WAIT_CONFIRMATION"
            row["kap_blocked"] = True
            row["entry_reasons"] = [f"[KAP] {kap.get('reason', 'Önemli olay açıklaması var')}; temkinli beklenmeli"] + list(row.get("entry_reasons") or [])
            return row
    except Exception:
        pass
    # A SINIFI KALITE KAPISI: secici giris — tatli bolge + hacim + akis +
    # (sektor dalgasi VEYA birikim). Uymayanlar girişe alinmaz, izlemeye duser.
    a_ok, a_reasons = _v8_a_class_gate(row, sym, data)
    row["a_class_ok"] = a_ok
    if not a_ok:
        row["entry_status"] = "WAIT_CONFIRMATION"
        row["a_class_rejected"] = True
        row["entry_reasons"] = ["[A SINIFI] " + "; ".join(a_reasons)] + list(row.get("entry_reasons") or [])
        return row
    live_price = data.get("Price") or row.get("price") or 0
    cstate, cmsg = _v8_entry_confirmation(sym, live_price)
    row["confirm_state"] = cstate
    row["confirm_message"] = cmsg
    if cstate == "REJECTED":
        row["entry_status"] = "WAIT_CONFIRMATION"
        row["entry_reasons"] = [f"[TEYİT] {cmsg}"] + list(row.get("entry_reasons") or [])
    return row

def auto_send_v8_signals():
    """GERCEK giris onayli V8 sinyallerini (erken adaylar haric) otomatik olarak
    Telegram kanalina TEK GRUPLU OZET olarak gonderir.
    - Hisse basina gunde EN FAZLA 1 sinyal (gunluk oncelikli, saatlik ikame).
    - Gonderim kaydi veritabaninda kalici: yeniden baslamada tekrar yok.
    - Ayi piyasasinda sinyal gitmez; Telegram ayarlari yoksa sessiz atlar."""
    try:
        from datetime import datetime as _dt
        from services.telegram_bot import send_v8_entry_signals_group as _send_group
        from v8_engine.database import V8Database as _V8DB
        all_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
        cache_ts = GLOBAL_DASHBOARD_CACHE.get("cache_timestamp")
        _today = _dt.now().strftime("%Y-%m-%d")
        if len(_V8_TG_SENT) > 500:
            _V8_TG_SENT.clear()

        # Kalici tekrar engeli: bugun gonderilenleri DB'den oku (bellek +
        # DB birlesik set; restart sonrasi tekrar mesaj gitmez).
        try:
            conn = _V8DB.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT symbol FROM v8_tg_sent WHERE day=?", (_today,))
            for r in cur.fetchall():
                _V8_TG_SENT.add((_today, r["symbol"]))
            conn.close()
        except Exception:
            pass

        regime_locked = _v8_regime_locked()
        regime_raw = (GLOBAL_DASHBOARD_CACHE.get("v8_market_regime") or {}).get("regime", "")
        _V8_REGIME_TR_MAP = {
            "STRONG_BULL": "GÜÇLÜ BOĞA (RALLİ)", "BULL": "BOĞA (YÜKSELİŞ TRENDİ)",
            "NEUTRAL": "NÖTR (YATAY / DENGE)", "BEAR": "AYI (DÜŞÜŞ BASKISI)",
            "STRONG_BEAR": "GÜÇLÜ AYI (SERT SATIŞ)",
        }
        try:
            scan_time = _dt.fromtimestamp(float(cache_ts)).strftime("%d.%m.%Y %H:%M") if cache_ts else ""
        except (TypeError, ValueError, OSError):
            scan_time = ""

        pending = []
        for sym, data in all_stats.items():
            # TEK SINYAL KURALI: hisse basina gunde 1. Gunluk kirilim varsa
            # o kullanilir; yoksa saatlik. Ikisi birden ASLA gonderilmez.
            key = (_today, sym)
            if key in _V8_TG_SENT:
                continue
            if regime_locked:
                continue
            bo = data.get("v8_breakout")
            intra = data.get("v8_breakout_1h") or {}
            daily_ok = bool(bo and bo.get("is_breakout") and (data.get("v8_execution") or {}).get("entry_status") == "ENTER")
            intra_ok = bool(intra.get("breakout", {}).get("is_breakout") and intra.get("entry_status") == "ENTER")
            if daily_ok:
                bo_row, reasons = bo, list((data.get("v8_execution") or {}).get("reasons") or [])
            elif intra_ok:
                bo_row, reasons = intra.get("breakout") or {}, ["1 saatlik barda kırılım teyidi (gün içi sinyal)"] + list(intra.get("reasons") or [])
            else:
                continue
            entry = float(data.get("Price") or data.get("Daily_Close") or 0)
            if entry <= 0:
                continue
            # KAP HABER FILTRESI: onemli olay duyurusu varsa sinyal gitmez.
            try:
                from services.kap_news import check_symbol as _kap_check
                if _kap_check(sym).get("blocked"):
                    continue
            except Exception:
                pass
            # A SINIFI KALITE KAPISI: secici giris yoksa kanala sinyal gitmez.
            if not _v8_a_class_gate({}, sym, data)[0]:
                continue
            # T+3 DAKIKA TEYIDI: teyit gecmeden telegrama sinyal gitmez.
            cstate, _cmsg = _v8_entry_confirmation(sym, data.get("Price") or entry)
            if cstate != "CONFIRMED":
                continue
            try:
                atr_pct = float((bo_row.get("metrics") or {}).get("atr_pct") or 0)
            except (TypeError, ValueError):
                atr_pct = 0.0
            if atr_pct > 0:
                stop_d = max(2.0, min(8.0, atr_pct * 1.5))
                t1_d = max(2.0, min(10.0, atr_pct * 1.5))
                t2_d = max(3.0, min(15.0, atr_pct * 2.5))
            else:
                stop_d, t1_d, t2_d = 5.0, 3.0, 5.0
            pending.append({
                "symbol": sym,
                "entry_price": entry,
                "stop_price": entry * (1 - stop_d / 100.0),
                "target1": entry * (1 + t1_d / 100.0),
                "target2": entry * (1 + t2_d / 100.0),
                "breakout_score": bo_row.get("breakout_score", 0),
                "fakeout_risk": bo_row.get("fakeout_risk", 0),
                "reason": (reasons or [""])[0],
                "market_regime": _V8_REGIME_TR_MAP.get(regime_raw, regime_raw),
                "scan_time": scan_time,
            })

        if not pending:
            return
        ok = _send_group(pending)
        if ok:
            for s in pending:
                _V8_TG_SENT.add((_today, s["symbol"]))
            try:
                conn = _V8DB.get_connection()
                cur = conn.cursor()
                now_iso = _dt.now().isoformat()
                for s in pending:
                    cur.execute(
                        "INSERT OR IGNORE INTO v8_tg_sent (day, symbol, sent_at) VALUES (?, ?, ?)",
                        (_today, s["symbol"], now_iso),
                    )
                conn.commit()
                conn.close()
            except Exception:
                pass
            logger.info("[V8-TG] Gruplu sinyal ozeti gonderildi: %s hisse", len(pending))
        else:
            logger.info("[V8-TG] Gruplu sinyal gonderilemedi (telegram ayarlari?)")
    except Exception as tg_err:
        logger.error("[V8-TG] Otomatik telegram hatasi: %s", tg_err)

@app.route('/api/v8/backtest/run', methods=['POST'])
def api_v8_backtest_run():
    """Geçmiş veri üzerinde V8 strateji backtest'ini arka planda başlatır."""
    try:
        from v8_engine.backtest import start_backtest
        res = start_backtest(BIST50_SYMBOLS, days=500)
        return jsonify(res)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v8/backtest/result', methods=['GET'])
def api_v8_backtest_result():
    try:
        from v8_engine.backtest import get_state
        return jsonify(get_state())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v8/kap/status', methods=['GET'])
def api_v8_kap_status():
    """KAP bulten servisinin erisim durumunu doner (filtre aktif mi?)."""
    try:
        from services.kap_news import refresh
        st = refresh()
        st["filter_active"] = bool(st.get("ok"))
        return jsonify(st)
    except Exception as e:
        return jsonify({"ok": False, "filter_active": False, "error": str(e)})

def _v8_live_price(data: dict) -> float:
    """Kartlarda gosterilecek fiyat: once CANLI Price (bayat degilse),
    yoksa Daily_Close. OZATD vakasi: cache'teki eski kapanis 4650 TL
    gorunuyordu; canli fiyat geldiginde o kullanilir."""
    try:
        if not data.get("Price_Stale"):
            p = float(data.get("Price") or 0)
            if p > 0:
                return p
        return float(data.get("Price") or data.get("Daily_Close") or 0)
    except (TypeError, ValueError):
        return 0.0


@app.route('/api/v8/radar/breakout', methods=['GET'])
def api_v8_radar_breakout():
    all_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
    if not all_stats:
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as _f_cache:
                _f_data = json.load(_f_cache)
                all_stats = _f_data.get("all_symbols_stats", {})
        except Exception:
            pass
    breakout_list = []
    cache_ts = GLOBAL_DASHBOARD_CACHE.get("cache_timestamp")

    for sym, data in all_stats.items():
        # BAYAT FIYAT KORUMASI: bugun taze fiyat gelmemis semboller
        # (OZATD gibi cok dusuk likiditeliler) eski fiyatiyla kart uretmez.
        if data.get("Price_Stale") and not data.get("v8_breakout", {}).get("is_breakout"):
            continue
        bo = data.get("v8_breakout")
        if bo and bo.get("is_breakout"):
            row = dict(bo)
            row["symbol"] = sym
            row["price"] = _v8_live_price(data)
            row["change_pct"] = data.get("Change_Pct", 0.0)
            row["volume"] = data.get("Volume", 0)
            row["volume_strength"] = _stats_rel_vol(data)
            row["scan_timestamp"] = cache_ts
            row["entry_status"] = data.get("v8_execution", {}).get("entry_status", "UNKNOWN")
            row["entry_reasons"] = data.get("v8_execution", {}).get("reasons", [])
            breakout_list.append(_v8_gate_enter_row(row, sym, data))
            continue

        # Gunluk kirilim yoksa 1 saatlik kirilim teyidine bak (daha erken sinyal):
        # 1h barda gercek kirilim + ENTER karari varsa gun ici AL adayi olarak ekle.
        if not (bo and bo.get("is_breakout")):
            intra = data.get("v8_breakout_1h") or {}
            intra_bo = intra.get("breakout") or {}
            if intra_bo.get("is_breakout") and intra.get("entry_status") == "ENTER":
                row = dict(intra_bo)
                row["symbol"] = sym
                row["price"] = _v8_live_price(data)
                row["change_pct"] = data.get("Change_Pct", 0.0)
                row["volume"] = data.get("Volume", 0)
                row["volume_strength"] = _stats_rel_vol(data)
                row["scan_timestamp"] = cache_ts
                row["entry_status"] = "ENTER"
                row["entry_reasons"] = ["1 saatlik barda kırılım teyidi (gün içi sinyal)"] + list(intra.get("reasons") or [])
                row["intraday_signal"] = True
                row["momentum_speed"] = intra.get("momentum_speed", "NORMAL")
                row["timeframe_quality"] = intra.get("timeframe_quality", 0)
                breakout_list.append(_v8_gate_enter_row(row, sym, data))
                continue

        # Kırılım yokken endpoint'in boş dönmesi V8'in 600+ hisseyi
        # taramadığı izlenimini veriyordu. Discovery sonuçlarını da bekleme
        # listesine ekle; gerçek kırılım oluştuğunda yukarıdaki karar yolu
        # yine önceliklidir.
        disc = data.get("v8_discovery") or {}
        state = disc.get("state")
        if state in ("READY", "PREPARING", "WATCH"):
            metrics = disc.get("metrics") or {}
            rel_vol = _stats_rel_vol(data)
            breakout_list.append({
                "symbol": sym,
                "price": _v8_live_price(data),
                "change_pct": data.get("Change_Pct", 0.0),
                "volume": data.get("Volume", 0),
                "is_breakout": False,
                "status": "DISCOVERY_" + state,
                "breakout_score": disc.get("preparation_score", 0.0),
                "fakeout_risk": 0.0,
                "metrics": {
                    "relative_volume": rel_vol,
                    "rsi": data.get("RSI", 50.0),
                },
                "volume_strength": rel_vol,
                "scan_timestamp": cache_ts,
                "entry_status": "WAIT",
                "entry_reasons": disc.get("reasons") or [
                    "Kırılım bekleniyor; hazırlık sinyali mevcut."
                ],
                "momentum_speed": "PREPARING",
            })
        elif data.get("Daily_Close") or data.get("Price"):
            # V8 verisi geçici olarak boşsa günlük taramayı da tamamen
            # kaybetme; bunları AL değil, düşük öncelikli BEKLE adayı yap.
            price = _v8_live_price(data)
            change = float(data.get("Change_Pct") or 0)
            rel_vol = _stats_rel_vol(data)
            fallback_score = max(35.0, min(65.0, 48.0 + change * 2.0 + (rel_vol - 1.0) * 5.0))
            breakout_list.append({
                "symbol": sym,
                "price": price,
                "change_pct": change,
                "volume": data.get("Volume", 0),
                "is_breakout": False,
                "status": "DISCOVERY_WATCH",
                "breakout_score": round(fallback_score, 1),
                "fakeout_risk": 0.0,
                "metrics": {"relative_volume": rel_vol, "rsi": data.get("RSI", 50.0)},
                "volume_strength": rel_vol,
                "scan_timestamp": cache_ts,
                "entry_status": "WAIT",
                "entry_reasons": ["Günlük tarama adayı; V8 kırılım teyidi bekleniyor."],
                "momentum_speed": "NORMAL",
            })
            
    # Siralama: Oncelikle kaliteli kirilimlar
    breakout_list = sorted(
        breakout_list,
        key=lambda x: (
            x.get("entry_status") == "ENTER",
            x.get("breakout_score", 0) - x.get("fakeout_risk", 0),
        ),
        reverse=True,
    )[:80]

    # Hazırlık adayları gerçek kırılım ve teyit olmadan ENTER yapılmaz.
    # Böylece gösterge yalnızca motordan gelen gerçek ENTER durumunu sayar.
    # V8 sinyalleri uygulama içinde kalır; Telegram'a yalnızca simülasyon olayları gider.


    # SENARYO PLANI: guncel rejime gore islem parametreleri kartlara islenir.
    # Bogada hedefler genisler, notrde standart, volatilitede daralir,
    # ayida kilit zaten uygulanir.
    try:
        from v8_engine.playbook import get_scenario
        _regime_now_pb = (GLOBAL_DASHBOARD_CACHE.get("v8_market_regime") or {}).get("regime", "NEUTRAL")
        _scenario = get_scenario(_regime_now_pb)
        for row in breakout_list:
            row["scenario"] = {
                "label": _scenario["label"],
                "icon": _scenario["icon"],
                "risk_pct": _scenario["risk_pct"],
                "tp1_mult": _scenario["tp1_mult"],
                "tp2_mult": _scenario["tp2_mult"],
                "stop_mult": _scenario["stop_mult"],
                "posture": _scenario["posture"],
            }
    except Exception:
        pass

    # SAVUNMA MODU gunluk limiti: AYI gununde en fazla 1 savunma islemi.
    # En yuksek kirilim skorlu aday kazanir, digerleri tekrar kilitlenir.
    _def_rows = [r for r in breakout_list if r.get("defense_mode") and (r.get("entry_status") or "").upper() == "ENTER"]
    if len(_def_rows) > 1:
        _def_rows.sort(key=lambda r: r.get("breakout_score") or 0, reverse=True)
        for r in _def_rows[1:]:
            r["entry_status"] = "WAIT_CONFIRMATION"
            r["defense_mode"] = False
            r["entry_reasons"] = ["[SAVUNMA] Ayı gününde en fazla 1 savunma işlemi açılır; bu aday limite takıldı"] + list(r.get("entry_reasons") or [])

    # TAVAN RİSKİ KAPISI: gun ici +%9.2 ve uzerinde olan hisseler "tavan
    # kovalama" bolgesindedir; BIST tavan kilit (%10) riski tasir.
    # Acikca UZAK DUR (NO_ENTRY) olarak isaretlenir; UI izleme kartlarina
    # almaz, erken aday promosyonu zaten uygulanamaz.
    for row in breakout_list:
        try:
            chg = float(row.get("change_pct") or row.get("intraday_change_pct") or 0)
        except (TypeError, ValueError):
            chg = 0.0
        if chg >= 9.2:
            row["entry_status"] = "NO_ENTRY"
            row["ceiling_risk"] = True
            row["entry_reasons"] = [
                f"[TAVAN RİSKİ] +{chg:.1f} ile tavana kilitli/kovalama bölgesinde"
            ] + list(row.get("entry_reasons") or [])

    return jsonify({"status": "success", "data": breakout_list})

@app.route('/api/v8/radar/discovery', methods=['GET'])
def api_v8_radar_discovery():
    all_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
    if not all_stats:
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as _f_cache:
                _f_data = json.load(_f_cache)
                all_stats = _f_data.get("all_symbols_stats", {})
        except Exception:
            pass
    discovery_list = []
    cache_ts = GLOBAL_DASHBOARD_CACHE.get("cache_timestamp")
    
    for sym, data in all_stats.items():
        disc = data.get("v8_discovery")
        if disc and disc.get("state") in ["READY", "PREPARING", "WATCH"]:
            # Combine some essential pricing data (cache'teki sozlugu DEGISTIRME; kopya uzerinde calis)
            disc = dict(disc)
            disc["metrics"] = dict(disc.get("metrics") or {})
            disc["metrics"]["relative_volume"] = _stats_rel_vol(data)
            disc["symbol"] = sym
            disc["price"] = _v8_live_price(data)
            disc["change_pct"] = data.get("Change_Pct", 0.0)
            disc["volume"] = data.get("Volume", 0)
            disc["volume_strength"] = _stats_rel_vol(data)
            disc["scan_timestamp"] = cache_ts
            discovery_list.append(disc)
        elif data.get("Daily_Close") or data.get("Price"):
            price = _v8_live_price(data)
            change = float(data.get("Change_Pct") or 0)
            rel_vol = _stats_rel_vol(data)
            discovery_list.append({
                "symbol": sym,
                "price": price,
                "change_pct": change,
                "volume": data.get("Volume", 0),
                "state": "WATCH",
                "preparation_score": round(max(35.0, min(65.0, 48.0 + change * 2.0 + (rel_vol - 1.0) * 5.0)), 1),
                "reasons": ["Günlük tarama adayı; V8 hazırlık teyidi bekleniyor."],
                "metrics": {"relative_volume": rel_vol},
                "volume_strength": rel_vol,
                "scan_timestamp": cache_ts,
            })
            
    # Puanlara gore sirala
    discovery_list = sorted(discovery_list, key=lambda x: x.get("preparation_score", 0), reverse=True)[:100]
    return jsonify({"status": "success", "data": discovery_list})

@app.route('/api/v8/entry-approval', methods=['POST'])
def api_v8_entry_approval():
    """Deterministic V8 entry gate; never fabricates missing market evidence."""
    try:
        from v8_engine.entry_approval import evaluate_entry_approval
        payload = request.get_json(force=True, silent=True) or {}
        result = evaluate_entry_approval(
            regime=payload.get("regime"),
            breakout=payload.get("breakout"),
            risk=payload.get("risk"),
            warrant=payload.get("warrant"),
        )
        return jsonify({"status": "success", "data": result})
    except Exception:
        logging.exception("V8 entry approval failed")
        return jsonify({"status": "error", "message": "Giriş onayı hesaplanamadı"}), 500


@app.route('/api/v8/market/regime', methods=['GET'])
def api_v8_market_regime():
    regime_data = GLOBAL_DASHBOARD_CACHE.get("v8_market_regime", {"regime": "UNKNOWN", "score": 50.0, "xu100_trend": 0.0})
    return jsonify(regime_data)

@app.route('/api/v8/playbook', methods=['GET'])
def api_v8_playbook():
    """Senaryo plani: guncel rejim + pozisyon/risk/hedef parametreleri +
    sektorsel dalga nabzi + islem basi kâr projeksiyonu."""
    try:
        from v8_engine.playbook import get_scenario, sector_pulse
        regime_data = GLOBAL_DASHBOARD_CACHE.get("v8_market_regime", {}) or {}
        regime = regime_data.get("regime", "NEUTRAL")
        scenario = get_scenario(regime)
        return jsonify({
            "status": "success",
            "scenario": scenario,
            "regime_detail": {
                "score": regime_data.get("score"),
                "xu100_trend": regime_data.get("xu100_trend"),
                "volatility_state": regime_data.get("volatility_state"),
            },
            "sector_pulse": sector_pulse(GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})),
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v8/weekly', methods=['GET'])
def api_v8_weekly():
    """HAFTALIK KÂR PANOSU: haftalik +X% gerceklesme, %6 hedefe mesafe,
    kâr koruma valfi durumu ve rejime gore dinamik risk/pozisyon plani.
    Hem simulasyon hem kullanicinin manuel islemleri ayni panoda toplanir."""
    try:
        from v8_engine.playbook import get_scenario
        from services.trade_database import get_connection as _td_conn
        from datetime import datetime as _dtw, timezone, timedelta as _tdw
        now = _dtw.now(ZoneInfo("Europe/Istanbul"))
        owner = "local:nebioglur"
        target_pct = 6.0

        # Pazartesi hafta basi (Python'da hesaplanir: hem SQLite hem PG uyumlu).
        monday = (now.date() - _tdw(days=now.weekday())).strftime("%Y-%m-%d")
        week_pnl = 0.0
        trades_count = 0
        wins = 0
        losses = 0
        open_positions = 0
        base_equity = 0.0
        conn = _td_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(SUM(pnl_val),0) p, COUNT(*) c, "
            "SUM(CASE WHEN pnl_val > 0 THEN 1 ELSE 0 END) w, "
            "SUM(CASE WHEN pnl_val <= 0 THEN 1 ELSE 0 END) l, "
            "SUM(CASE WHEN exit_price IS NULL THEN 1 ELSE 0 END) o "
            "FROM trades WHERE owner=? AND date_str >= ?",
            (owner, monday),
        )
        row = cur.fetchone()
        if row:
            week_pnl = float(row["p"] or 0)
            trades_count = int(row["c"] or 0)
            wins = int(row["w"] or 0)
            losses = int(row["l"] or 0)
            open_positions = int(row["o"] or 0)
        cur.execute(
            "SELECT end_equity FROM equity_log WHERE owner=? AND date_str < ? "
            "ORDER BY date_str DESC LIMIT 1",
            (owner, monday),
        )
        eq = cur.fetchone()
        if eq and eq["end_equity"]:
            base_equity = float(eq["end_equity"])
        else:
            cur.execute(
                "SELECT start_equity FROM equity_log WHERE owner=? ORDER BY date_str ASC LIMIT 1",
                (owner,),
            )
            start = cur.fetchone()
            base_equity = float(start["start_equity"]) if start and start["start_equity"] else 100000.0
        conn.close()

        week_pct = (week_pnl / base_equity * 100.0) if base_equity > 0 else 0.0
        valve_on = week_pct >= target_pct
        regime_data = GLOBAL_DASHBOARD_CACHE.get("v8_market_regime", {}) or {}
        regime = regime_data.get("regime", "NEUTRAL")
        scenario = get_scenario(regime)
        remaining_pct = max(0.0, target_pct - week_pct)

        return jsonify({
            "status": "success",
            "week_label": now.strftime("%d.%m") + " - " + (now + _tdw(days=4)).strftime("%d.%m.%Y"),
            "base_equity": round(base_equity, 2),
            "week_pnl": round(week_pnl, 2),
            "week_pct": round(week_pct, 2),
            "target_pct": target_pct,
            "remaining_pct": round(remaining_pct, 2),
            "progress_pct": round(min(150.0, week_pct / target_pct * 100.0), 1) if target_pct > 0 else 0,
            "valve_on": valve_on,
            "trades_count": trades_count,
            "wins": wins,
            "losses": losses,
            "open_positions": open_positions,
            "regime": regime,
            "scenario": {
                "label": scenario.get("label"),
                "icon": scenario.get("icon"),
                "risk_pct": scenario.get("risk_pct"),
                "max_positions": scenario.get("max_positions"),
                "tp1_mult": scenario.get("tp1_mult"),
                "tp2_mult": scenario.get("tp2_mult"),
            },
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def api_logs():
    try:
        if not session.get('logged_in'):
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
        log_file = "data/system_logs.txt"
        if not os.path.exists(log_file):
            return jsonify({"status": "success", "logs": "Henüz log kaydı yok."})
            
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        return jsonify({"status": "success", "logs": "".join(lines[-200:])})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500


@app.route('/api/detective', methods=['GET'])
def api_detective():
    """PIYASA DEDEKTIFI: tum hisseler icin davranissal metrik satirlari."""
    try:
        from services.detective_engine import get_rows, start_background_loop
        start_background_loop()  # gunicorn worker'larda garanti baslatma
        data = get_rows()
        safe_data = sanitize_for_json(data)
        return jsonify({"status": safe_data.get("status", "ok"),
                        "rows": safe_data.get("rows", []),
                        "summary": safe_data.get("summary", {}),
                        "built_at": safe_data.get("built_at"),
                        "error": safe_data.get("error")})
    except Exception as e:
        import traceback
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500


@app.route('/api/detective/detail/<symbol>', methods=['GET'])
def api_detective_detail(symbol):
    """Dedektif paneli: olay zinciri, ayni gecmis, karakter, hareket zinciri."""
    try:
        from services.detective_engine import get_detail
        d = get_detail(symbol)
        if not d:
            return jsonify({"status": "error", "message": "Veri henüz hazır değil ya da sembol kapsamda değil."}), 404
        return jsonify({"status": "success", "detail": sanitize_for_json(d)})
    except Exception as e:
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500


@app.route('/api/dip_breakout', methods=['GET'])
def api_dip_breakout():
    """DIP & KIRILIM RADARI: akilli dip skoru (10 kriter), 3 asamali kirilim,
    tuzak riski, dip-kirilim mesafesi ve kategori gruplari."""
    try:
        from services.dip_breakout_engine import get_rows, start_background_loop
        start_background_loop()
        d = get_rows()
        # tani: yeni hisse tarayici durumu (0 donerse nedenini gormek icin)
        diag = {}
        try:
            import yfinance
            from services.universe_scanner import _cache as _usc
            diag = {
                "yfinance_version": getattr(yfinance, "__version__", "?"),
                "scanner_built_at": str(_usc.get("built_at")),
                "scanner_error": _usc.get("error"),
                "scanner_count": len(_usc.get("new_listings") or []),
                "scanner_universe": _usc.get("total_universe"),
            }
        except Exception as de:
            diag = {"diag_error": str(de)}
        safe = sanitize_for_json(d)
        return jsonify({"status": "ok" if safe.get("rows") else "empty",
                        "rows": safe.get("rows", []),
                        "summary": safe.get("summary", {}),
                        "built_at": safe.get("built_at"),
                        "diag": diag,
                        "error": safe.get("error")})
    except Exception as e:
        import traceback
        logging.exception("API operation failed")
        return jsonify({"status": "error", "message": "İşlem sırasında hata oluştu"}), 500


_BACKGROUND_SERVICES_STARTED = False

def start_background_services():
    """Start the single-process background workers for both WSGI and local runs."""
    global _BACKGROUND_SERVICES_STARTED
    if _BACKGROUND_SERVICES_STARTED:
        return
    _BACKGROUND_SERVICES_STARTED = True

    if os.environ.get("ENABLE_BACKGROUND_SERVICES", "true").lower() != "true":
        logging.info("Background services disabled by configuration")
        return

    try:
        threading.Thread(target=background_scanner, daemon=True, name="background-scanner").start()
    except Exception:
        logging.exception("Background scanner could not start")
    try:
        threading.Thread(target=simulation_loop, daemon=True, name="simulation-loop").start()
    except Exception:
        logging.exception("Simulation loop could not start")
    try:
        start_live_data_collector()
    except Exception:
        logging.exception("Live data collector could not start")
    try:
        from services.detective_engine import start_background_loop as start_detective_loop
        start_detective_loop()
    except Exception:
        logging.exception("Detective engine loop could not start")
    try:
        from services.dip_breakout_engine import start_background_loop as start_dip_loop
        start_dip_loop()
    except Exception:
        logging.exception("Dip/breakout engine loop could not start")


@app.route('/api/telegram/test_suite', methods=['POST'])
def api_telegram_test_suite():
    """Telegram uçtan uca bildirim test paketi (AL, TP1, Seans Sonu, Finans Raporu, %90 Sıralama)."""
    try:
        from services.telegram_bot import (
            notify_sim_trade,
            get_special_ranking_candidates,
            send_special_ranking_alert,
            send_simulation_report,
            send_morning_compass_bulletin,
            send_telegram_message
        )
        data = request.get_json(force=True, silent=True) or {}
        test_type = data.get('type', 'all')
        results = {}
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today_s = datetime.now().strftime('%Y-%m-%d')

        dummy_trade = {
            'symbol': 'THYAO.IS',
            'entry_time': now_str,
            'entry_price': 304.50,
            'shares': 65,
            'entry_score': 94.0,
            'entry_checks': 'Ana trend, RSI dengeli, Hacim teyidi, VWAP üstü | Bonuslar: 💸 Akıllı Para, 🔥 Süper Hacim',
            'strategy_name': 'V8 Boğa Koşucusu (%90+ Elit)',
            'exit_time': now_str,
            'pnl_val': 435.50,
            'pnl_pct': 2.20
        }

        if test_type in ('all', 'buy'):
            ok = notify_sim_trade('THYAO.IS', 'AL', 304.50, 0.0, 'Hacim Patlaması & EMA Kırılımı', today_s, dummy_trade)
            results['sim_buy'] = ok

        if test_type in ('all', 'tp1'):
            ok = notify_sim_trade('THYAO.IS', 'SAT (TP1)', 311.20, 2.20, '1. Kâr Alındı, Stop Maliyete Çekildi (Sıfır Risk)', today_s, dummy_trade)
            results['sim_tp1'] = ok

        if test_type in ('all', 'eod'):
            ok = notify_sim_trade('THYAO.IS', 'SAT (GUN SONU)', 314.80, 3.38, '17:50 Seans Sonu Nakde Geçiş', today_s, dummy_trade)
            results['sim_eod'] = ok

        if test_type in ('all', 'ranking'):
            all_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
            candidates = get_special_ranking_candidates(all_stats, top_n=3)
            if candidates:
                ok = send_special_ranking_alert(candidates)
                results['special_ranking'] = ok
            else:
                results['special_ranking'] = 'Filtrelere uyan aday bulunamadı'

        return jsonify({'status': 'success', 'results': results})
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'İşlem sırasında hata oluştu'}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    start_background_services()
    app.run(host="0.0.0.0", port=port)
