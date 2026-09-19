import os
import sys
import math
import json
import time
import threading
import time
from datetime import datetime, timedelta

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
from flask_cors import CORS
import feedparser

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


def load_dashboard_cache():
    import json, os
    from datetime import datetime
    
    # Once DB'den (kalici veritabanindan) yuklemeyi dene
    try:
        from services.trade_database import get_connection
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM live_settings WHERE key = 'dashboard_cache'")
            row = cur.fetchone()
            if row and row["value"]:
                data = json.loads(row["value"])
                today_str = datetime.now().strftime("%Y-%m-%d")
                if data.get("cache_date") != today_str:
                    print(f"[CACHE] DB'den onceki gunun cache'i yuklendi ({len(data.get('all_symbols_stats', {}))} hisse, tarih {data.get('cache_date')}) - yeni tarama ile guncellenecek")
                else:
                    print(f"[CACHE] DB'den BUGUNUN cache'i yuklendi ({len(data.get('all_symbols_stats', {}))} hisse, tarih {data.get('cache_date')})")
                return data
    except Exception as e:
        print(f"[CACHE] DB yukleme hatasi: {e}")
        
    # Eger DB bos ise (veya hata verdiyse), dosyadan yuklemeyi dene
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                today_str = datetime.now().strftime("%Y-%m-%d")
                if data.get("cache_date") != today_str:
                    print(f"[CACHE] DOSYADAN onceki gunun cache'i yuklendi ({len(data.get('all_symbols_stats', {}))} hisse, tarih {data.get('cache_date')})")
                return data
    except Exception:
        pass
    return {}

def sync_to_github():
    try:
        import subprocess
        # Sadece data dizinini ve dashboard_cache'i gonder
        git_cmd = r"C:\Users\nebioglur\mingit\cmd\git.exe"
        if not os.path.exists(git_cmd):
            git_cmd = "git" # sistem path'inde varsa
        
        subprocess.run([git_cmd, "add", "dashboard_cache.json", "data/tavan_daily_audit.json", "data/trades_db.sqlite"], check=False)
        res = subprocess.run([git_cmd, "commit", "-m", "chore: auto-sync live data [skip ci]"], capture_output=True, text=True)
        if "nothing to commit" not in res.stdout:
            subprocess.run([git_cmd, "push", "origin", "main"], check=False)
            print("[GITHUB] Veriler canli sunucu icin basariyla push edildi.")
    except Exception as e:
        print(f"[GITHUB ERROR] {e}")

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
    now = now or datetime.now()
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
                now = _dt.now()
                weekday = now.weekday() < 5
                t = now.time()
                in_session = t >= _dt.strptime("09:50", "%H:%M").time() and t <= _dt.strptime("18:15", "%H:%M").time()
                if weekday and in_session:
                    d_str = now.strftime("%Y-%m-%d")
                    try:
                        MarketDataManager.fetch_and_store_intraday(d_str, period="5d")
                    except Exception as coll_err:
                        print(f"[LIVE DATA] toplama hatasi: {coll_err}")
                        
                    # FAST PRICE UPDATE
                    try:
                        global GLOBAL_DASHBOARD_CACHE
                        if isinstance(GLOBAL_DASHBOARD_CACHE, dict) and "all_symbols_stats" in GLOBAL_DASHBOARD_CACHE:
                            print("[LIVE DATA] Hızlı fiyat güncellemesi başlatılıyor...")
                            import yfinance as _yf
                            from config.bist_symbols import BIST_SYMBOLS
                            
                            syms_to_fetch = [s + ".IS" if not s.endswith(".IS") else s for s in BIST_SYMBOLS]
                            # Hızlı 1 günlük indirme
                            fast_data = _yf.download(syms_to_fetch, period="1d", interval="1d", threads=True, progress=False)
                            
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
                                        if not math.isnan(close_px):
                                            GLOBAL_DASHBOARD_CACHE["all_symbols_stats"][sym]["Price"] = round(close_px, 2)
                                            # Ayrıca değişim yüzdesini de güncelleyebiliriz
                                            prev = float(row["Open"]) if "Open" in row else None
                                            if prev and not math.isnan(prev) and prev > 0:
                                                GLOBAL_DASHBOARD_CACHE["all_symbols_stats"][sym]["Change_Pct"] = round(((close_px - prev) / prev) * 100, 2)
                                            updates += 1
                                    except Exception:
                                        pass
                                        
                            if updates > 0:
                                from datetime import datetime as _dt
                                GLOBAL_DASHBOARD_CACHE["cache_date"] = _dt.now().strftime("%Y-%m-%d")
                                save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
                                print(f"[LIVE DATA] {updates} hissenin canlı fiyatları Dashboard'a yansıtıldı!")
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
    
    # Sunucu başlatıldığında tek seferlik Telegram kontrol/açılış bildirimi gönder
    try:
        notif.send_system_startup_alert()
    except Exception as e_start:
        print(f"[BACKGROUND] Telegram açılış bildirimi hatası: {e_start}")
    
    def process_notifications(results):
        if not results or not isinstance(results, dict):
            return
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # 1. Tavan Adayları Bildirimleri (Aynı gün sadece 1 kez gönder)
        for tavan in results.get("tavan_adaylari", []):
            sym = tavan.get("Symbol")
            if sym and sent_tavan.get(sym) != today_str:
                notif.send_tavan_alert(sym, tavan.get("Score", 0), tavan.get("Report", ""), tavan.get("Position"), extra=tavan)
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
                save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
                
                # Hızlı Başlangıçta da sinyalleri DB'ye yaz (Simülasyon boş kalmasın)
                from services.market_data import MarketDataManager
                MarketDataManager.record_signals(fast_results["cache_date"], fast_1h_res.get("tavan_adaylari", []))
                MarketDataManager.fetch_and_store_intraday(fast_results["cache_date"])
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
            
            process_notifications(GLOBAL_DASHBOARD_CACHE)
            print("[BACKGROUND] Hızlı Başlangıç Faz 3 tamamlandı - Tüm fırsatlar HAZIR!")
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
                            
                            # Günlük simülasyonu çalıştır (kayıtlı her hesap için ayrı)
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
                            for _owner in _owners:
                                try:
                                    sim = SimulationEngine(owner=_owner)
                                    sim.run_daily_simulation(d_str)
                                except Exception as _sim_err:
                                    print(f"[BACKGROUND] Sim hatasi ({_owner}): {_sim_err}")

                            # Gün Sonu Simülasyon Telegram Raporu (18:10 Sonrası)
                            now_time = datetime.now()
                            if now_time.hour == 18 and now_time.minute >= 10:
                                try:
                                    import json, os
                                    from services.telegram_bot import send_simulation_report

                                    report_cache = "data/sent_sim_report.json"
                                    sent_today = False
                                    if os.path.exists(report_cache):
                                        with open(report_cache, "r") as f:
                                            cd = json.load(f)
                                            if cd.get("date") == d_str:
                                                sent_today = True

                                    if not sent_today:
                                        from services.trade_database import get_connection
                                        trades = []
                                        try:
                                            with get_connection() as conn:
                                                c = conn.cursor()
                                                _report_owner = os.environ.get('ADMIN_OWNER', 'local:nebioglur')
                                                c.execute("SELECT * FROM trades WHERE date_str=? AND owner=?", (d_str, _report_owner))
                                                trades = [dict(row) for row in c.fetchall()]
                                        except Exception as db_err:
                                            print(f"[SIM DB HATA] {db_err}")
                                        if trades:
                                            total_pnl = sum([t.get('pnl_val', 0) for t in trades])
                                            total_invested = sum([(t.get('shares',0) * t.get('entry_price',0)) for t in trades])
                                            pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
                                            
                                            success = send_simulation_report(len(trades), total_pnl, pct)
                                            if success:
                                                with open(report_cache, "w") as f:
                                                    json.dump({"date": d_str}, f)
                                except Exception as err:
                                    print(f"[SIM SİNYAL HATA] {str(err)}")
                            
                        except Exception as e_audit:
                            print(f"[BACKGROUND] Yeni Motor Hatası: {e_audit}")
                            import traceback
                            traceback.print_exc()
                        
                        # Github Cloud Data Sync (Statik sayfalar ve dış VPS'ler için)
                        sync_to_github()
                            
                        print("[BACKGROUND] 1h ve Tavan taraması tamamlandı, saatlik tavan denetçisine kaydedildi.")
                except Exception as e_1h:
                    print(f"[BACKGROUND] 1h Tarama hatası: {e_1h}")
                
                # Telegram bildirimlerini gonder
                process_notifications(GLOBAL_DASHBOARD_CACHE)
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
            now = datetime.datetime.now()
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
            now = datetime.now()
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



CORS(app)

# ============ SESSION AUTH (GÜVENLİK) ============
import os
from flask import request, Response, session, redirect, jsonify, render_template_string

app.secret_key = os.environ.get('SECRET_KEY', 'varant_pro_ultra_secret_2026_xyz')

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
    """Supabase access token'ini dogrular.
    Donus: (user_id, hata_mesaji). Basarida hata_mesaji=None.
    Token imzayi dogrulamadan cozulup iss'ten gercek proje tespit edilir ve
    token KENDI projesinin /auth/v1/user ucunda dogrulanir; olmazsa iss'ten
    turetilen diger proje adreslerinde denenir. Boylece token hangi Supabase
    projesinden gelirse gelsin dogrulanir (farkli proje imzasi -> "invalid
    JWT signature" hatasinin kok nedeni cozulur)."""
    import hashlib
    import time as _time
    import urllib.request
    import urllib.error
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    now = _time.time()
    cached = _user_token_cache.get(token_hash)
    if cached and cached[1] > now:
        return cached[0], None

    unverified = _decode_jwt_unverified(token)
    iss = (unverified or {}).get('iss') or ''
    ref = ((unverified or {}).get('app_metadata') or {}).get('project_ref') or ''
    print(f"[AUTH] Token iss teshisi: iss={iss[:90]} ref={ref[:24]} sub={str((unverified or {}).get('sub'))[:10]}")

    bases = []
    if iss:
        b = iss.split('/auth/v1')[0].rstrip('/')
        if b and b.startswith("http"):
            bases.append(b)
    if ref:
        proxy_base = f"https://supabase-api-prod.verdent.ai/p/{ref}"
        if proxy_base not in bases:
            bases.append(proxy_base)
    if SUPABASE_URL not in bases:
        bases.append(SUPABASE_URL)

    last_error = "yok"
    for base in bases:
        for key_try in (SUPABASE_PUBLISHABLE_KEY, None):
            try:
                user = _supabase_user_from_endpoint(base, token, key_try)
                user_id = user.get("id") or user.get("sub")
                if user_id:
                    # Guvenlik: imzasiz cozumlenen sub ile uyusmadigindan emin ol
                    if unverified and unverified.get('sub') and user_id != unverified.get('sub'):
                        print("[AUTH] user id, token sub ile uyusmadi, reddedildi")
                        break
                    _user_token_cache[token_hash] = (user_id, now + 120)
                    print(f"[AUTH] Token dogrulandi: {base}")
                    return user_id, None
            except urllib.error.HTTPError as e:
                body = e.read().decode('utf-8', 'ignore')[:160]
                last_error = f"{e.code} {body}"
                print(f"[AUTH] Dogrulama denemesi {base} (apikey={'var' if key_try else 'yok'}): {last_error}")
                # Imza hatasi: bu base token'i vermemis, siradaki base'i dene
                continue
            except Exception as e:
                last_error = f"istisna: {e}"
                print(f"[AUTH] Dogrulama denemesi {base} {last_error}")
                break
    return None, f"Token dogrulanamadi (iss={iss[:60] or 'yok'}) - Son hata: {last_error}"

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
    body = ("User-agent: *\n"
            "Allow: /\n"
            "Disallow: /api/\n\n"
            "Sitemap: https://varantradar-7.onrender.com/sitemap.xml\n")
    resp = make_response(body)
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


@app.route('/sitemap.xml')
def sitemap_xml():
    body = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            '  <url><loc>https://varantradar-7.onrender.com/</loc>'
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
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
    log_auth(f"Token alindi, ilk 10 hane: {token[:10]}...")
    user_id, err_msg = verify_supabase_token(token)
    if not user_id:
        log_auth(f"verify_supabase_token basarisiz: {err_msg}")
        return jsonify({"status": "error", "message": f"Token dogrulanmadi: {err_msg}"}), 401
    log_auth(f"Token gecerli, user_id: {user_id}")
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
    
    allowed = ['/login', '/logout', '/api/ping', '/api/auth_config', '/api/auth/session', '/api/client_log', '/api/system_logs_read']
    if request.path in allowed or request.path.startswith('/api/dashboard_init'): return
    
    # Allow static assets for login page
    if request.path.endswith('.css') or request.path.endswith('.js') or request.path.endswith('.png') or request.path.endswith('.woff2'):
        return

    # Arama motorlari dosyalari oturum kapisi disinda (SEO)
    if request.path in ('/robots.txt', '/sitemap.xml'):
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

@app.route('/login', methods=['GET'])
def login():
    # Giris artık tarayici tarafinda Verdent-managed Supabase Auth ile yapilir
    # (@verdent/auth-js builtin UI). Sunucu tarafinda form login yoktur.
    # CLASSIC_ONLY=1 ise (bagimsiz yedek site) sadece klasik kullanici/sifre formu gosterilir.
    try:
        with open('ui/login.html', 'r', encoding='utf-8') as f:
            html = f.read()
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
    valid_user = os.environ.get('ADMIN_USER', 'nebioglur')
    valid_pass = os.environ.get('ADMIN_PASS', '123')
    if username == valid_user and password == valid_pass:
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
        return jsonify({"status": "error", "message": str(e)}), 500

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
        
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df.empty:
            return jsonify({"status": "error", "message": "Veri bulunamadı"}), 404
            
        # Sütunları küçük harfe çevir (BacktestEngine öyle bekliyor)
        df.columns = [c[0].lower() if isinstance(c, tuple) else str(c).lower() for c in df.columns]
        df['date'] = df.index.astype(str)
        
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
        return jsonify({"status": "error", "message": str(e)}), 500

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
        response = make_response(send_from_directory('ui', 'index.html'))
    except Exception as e:
        import traceback
        return f'<pre>{traceback.format_exc()}</pre>', 500
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
        return jsonify({"status": "error", "message": str(e)}), 500

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
            hd = yf.Ticker(clean + ".IS").history(period="5d", interval="1d")
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
    
    last_updated = "Bilinmiyor"
    import os
    from datetime import datetime
    if os.path.exists("dashboard_cache.json"):
        mtime = os.path.getmtime("dashboard_cache.json")
        last_updated = datetime.fromtimestamp(mtime).strftime("%H:%M")
        
    return jsonify({
        "status": "success",
        "total_analyzed": total,
        "dashboard_data": clean_cache or {},
        "xu100_change": get_xu100_change(),
        "last_updated": last_updated,
        "market": market,
        "data_fresh": bool(market["is_open"]),
        "stale_data_suppressed": not market["is_open"]
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
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/scan', methods=['GET'])
def api_scan():
    """Hisse Radarı: BIST30 listesini tarar."""
    pool = BIST_SYMBOLS
    try:
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        results = scanner.scan_pool_bulk(pool).get("opportunities", [])
        return jsonify({"status": "success", "count": len(results), "results": sanitize_for_json(results)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/scan_bist50', methods=['GET'])
def api_scan_bist50():
    pool = BIST50_SYMBOLS
    try:
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        results = scanner.scan_pool_bulk(pool).get("opportunities", [])
        return jsonify({"status": "success", "count": len(results), "results": sanitize_for_json(results)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/scan_yildiz', methods=['GET'])
def api_scan_yildiz():
    pool = BIST_SYMBOLS
    try:
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        results = scanner.scan_pool_bulk(pool).get("opportunities", [])
        return jsonify({"status": "success", "count": len(results), "results": sanitize_for_json(results)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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
        return jsonify({"status": "error", "message": str(e)}), 500

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
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/scan_commodity', methods=['GET'])
def api_scan_commodity():
    pool = COMMODITY_SYMBOLS
    try:
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        results = scanner.scan_pool_bulk(pool).get("opportunities", [])
        return jsonify({"status": "success", "count": len(results), "results": sanitize_for_json(results)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/scan_crypto', methods=['GET'])
def api_scan_crypto():
    pool = CRYPTO_SYMBOLS
    try:
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        results = scanner.scan_pool_bulk(pool).get("opportunities", [])
        return jsonify({"status": "success", "count": len(results), "results": sanitize_for_json(results)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/system_logs_read', methods=['GET'])
def api_system_logs_read():
    """Gecici log okuma ucu"""
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
    return jsonify({"status": "alive", "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "cwd": os.getcwd()})

@app.route('/api/health', methods=['GET'])
def api_health():
    """Tüm veri sağlayıcılarının sağlık durumunu döndürür."""
    try:
        pipeline = DataPipeline()
        health_report = pipeline.get_health_report()
        return jsonify({"status": "success", "data": health_report})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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
        return jsonify({"status": "error", "message": str(e)}), 500

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
        return jsonify({"status": "error", "message": str(e)}), 500

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
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/simulation/live_orders', methods=['GET'])
def api_simulation_live_orders():
    try:
        from services.market_data import MarketDataManager
        import datetime
        # Canlı sistemde bugün olması lazım
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        date_str = request.args.get('date', today) 
        signals = MarketDataManager.get_signals(date_str)
        
        valid_signals = []
        for s in signals:
            score = float(s.get('score', 0))
            phase = str(s.get('morning_phase', ''))
            if score >= 80 and "NEGAT" not in phase and "UZAK DUR" not in phase:
                valid_signals.append(s)
                
        orders = []
        # ENDEKS KALKANI (Market Regime Filter)
        bist_chg = get_xu100_change()
        
        # 1. PİYASA GENİŞLİĞİ (Market Breadth - Suni Ralli Kalkanı)
        advancers = 0
        decliners = 0
        total_scanned = 0
        cache_data = globals().get("GLOBAL_DASHBOARD_CACHE", {})
        for cat, items in cache_data.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and "Change_Pct" in item:
                        total_scanned += 1
                        val = float(item["Change_Pct"])
                        if val > 0: advancers += 1
                        elif val < 0: decliners += 1
        
        ad_ratio = (advancers / total_scanned) if total_scanned > 0 else 0.5
        # Eğer endeks artıdaysa ama piyasadaki hisselerin %60'ından fazlası eksideyse = SUNİ RALLİ
        is_fake_rally = (bist_chg > 0 and ad_ratio < 0.40)
        
        # Suni rallide risk %80 daraltılır (Güvenilmez piyasa)
        is_bear_market = (bist_chg < -0.5)
        if is_fake_rally:
            base_allocation = 666.0
        else:
            base_allocation = 1500.0 if is_bear_market else 3333.0  
        
        # SAATLİK TUZAK (FAKEOUT) FİLTRESİ
        import datetime
        now_time = datetime.datetime.now().time()
        lunch_start = datetime.time(12, 30)
        lunch_end = datetime.time(14, 0)
        # Öğle tatili civarındaki sığ hacimli hareketleri filtrele
        is_fakeout_zone = (lunch_start <= now_time <= lunch_end)
        
        import json
        for s in valid_signals:
            morning_price = float(s.get('morning_price', 0))
            if morning_price <= 0: continue
            
            if is_fakeout_zone:
                # Sadece aşırı güçlü YZ favorileri fakeout saatinde geçebilir
                if s.get('score', 0) < 95:
                    continue
            
            meta = {}
            try:
                meta = json.loads(s.get('metadata', '{}'))
            except: pass
            
            # MTF ONAYI: Günlük EMA50 > EMA200 değilse pas geç (Katı filtre)
            e50 = meta.get('Daily_EMA50')
            e200 = meta.get('Daily_EMA200')
            if e50 is None or e200 is None:
                inds = meta.get('Indicators', {})
                e50 = inds.get('EMA_50')
                e200 = inds.get('EMA_200')
                
            if e50 and e200 and float(e50) <= float(e200):
                continue # MTF (Günlük) ana trend negatif, riske girme!
                
            entry_price = morning_price * 1.0015 # %0.15 slipaj payı
            # 2. KELLY KRITERI (Dinamik Pozisyon Boyutlandirma)
            ai_score = float(s.get('score', 60))
            win_prob = ai_score / 100.0
            reward_risk = 2.0
            kelly_fraction = max(0.1, min(1.0, win_prob - ((1.0 - win_prob) / reward_risk)))
            final_allocation = base_allocation * (kelly_fraction / 0.5)
            shares = int(final_allocation // entry_price)
            if shares <= 0: continue
            
            ceiling = float(s.get('ceiling_target', entry_price * 1.10))
            
            # ATR TABANLI DİNAMİK HEDEFLEME
            atr = meta.get('ATR')
            if atr and float(atr) > 0:
                atr_val = float(atr)
                stop_price = entry_price - (atr_val * 1.2)  # 1.2x ATR Stop
                tp1_price = entry_price + (atr_val * 1.5)   # 1.5x ATR TP1
                tp2_price = entry_price + (atr_val * 3.0)   # 3.0x ATR TP2 (or Ceiling)
                tp2_price = min(tp2_price, ceiling) # Tavandan fazlasını hedefleme
            else:
                stop_price = entry_price * 0.97
                tp1_price = entry_price * 1.05
                tp2_price = ceiling
            
            orders.append({
                'symbol': s['symbol'],
                'score': s['score'],
                'entry_price': round(entry_price, 2),
                'shares': shares,
                'total_volume': round(shares * entry_price, 2),
                'stop_price': round(stop_price, 2),
                'max_loss': round(shares * (entry_price - stop_price), 2),
                'tp1_price': round(tp1_price, 2),
                'tp2_price': round(tp2_price, 2)
            })
            
        return jsonify({
            "status": "success",
            "date": date_str,
            "orders": sanitize_for_json(sorted(orders, key=lambda x: x["score"], reverse=True))
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/simulation/terminal', methods=['GET'])
def api_simulation_terminal():
    """Anlik islem terminali durumu: acik pozisyonlar, son islemler, bakiye (hesaba ozel)."""
    try:
        from services.live_trade_monitor import get_terminal_state
        return jsonify({"status": "success", "terminal": sanitize_for_json(get_terminal_state(get_owner_key()))})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/simulation/terminal/open', methods=['POST'])
def api_simulation_terminal_open():
    """Manuel anlik alim (canlı pozisyon aç)."""
    try:
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
        return jsonify({"status": "error", "message": str(e)}), 500

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
        return jsonify({"status": "error", "message": str(e)}), 500

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
        return jsonify({"status": "error", "message": str(e)}), 500

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
        return jsonify({"status": "error", "message": str(e)}), 500

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
        return jsonify({"status": "error", "message": str(e)}), 500

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
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        return jsonify({"status": "error", "message": str(e)}), 500

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
        return jsonify({"status": "error", "message": str(e)}), 500

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
        return jsonify({"status": "error", "message": str(e), "trace": traceback.format_exc()}), 500


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
        return jsonify({"status": "error", "message": str(e)}), 500

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
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        return jsonify({"status": "error", "message": str(e)}), 500

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
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/tavan_history', methods=['GET'])
def api_tavan_history():
    try:
        from services.tavan_tracker import TavanAuditTracker
        # Arka plan taraması henüz ilk denetim kaydını yazmadıysa, mevcut
        # gerçek dashboard cache'inden bir canlı snapshot oluştur. Böylece
        # Render yeniden başlatmalarında istatistik ekranı boş kalmaz.
        today_str = datetime.now().strftime("%Y-%m-%d")
        audits = TavanAuditTracker.load_all_audits()
        if today_str not in audits:
            cached_candidates = GLOBAL_DASHBOARD_CACHE.get("tavan_adaylari", [])
            cached_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
            if cached_candidates and cached_stats:
                TavanAuditTracker.record_snapshot(
                    cached_candidates,
                    all_symbols_stats=cached_stats,
                    date_str=today_str,
                )
                TavanAuditTracker.update_daily_progress(
                    cached_stats,
                    date_str=today_str,
                )
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
        return jsonify(sanitize_for_json(res))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

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
        res = TavanAuditTracker.get_audit_report(date_str)
        return jsonify(sanitize_for_json(res))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/simulation/daily_pnl', methods=['GET'])
def api_simulation_daily_pnl():
    try:
        from services.trade_database import get_connection
        conn = get_connection()
        
        # Get all trades
        import sqlite3
        from contextlib import closing
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            owner = get_owner_key()
            # Fetch daily equity log (hesaba ozel)
            c.execute("SELECT * FROM equity_log WHERE owner=? ORDER BY date_str ASC", (owner,))
            equity_rows = c.fetchall()
            equity_curve = [dict(row) for row in equity_rows]
            if not equity_curve:
                from datetime import datetime
                equity_curve = [{"date_str": datetime.now().strftime("%Y-%m-%d"), "start_equity": 100000.0, "end_equity": 100000.0, "total_pnl": 0.0}]

            # Fetch closed trades (hesaba ozel)
            c.execute("SELECT * FROM trades WHERE owner=? ORDER BY entry_time DESC LIMIT 100", (owner,))
            trade_rows = c.fetchall()
            trades = [dict(row) for row in trade_rows]
            
            from services.statistics_engine import StatisticsEngine
            performance = StatisticsEngine.get_trade_performance(owner)
            return jsonify({
                "status": "success",
                "equity_curve": sanitize_for_json(equity_curve),
                "trades": sanitize_for_json(trades),
                "performance": sanitize_for_json(performance)
            })
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
        return jsonify({"status": "error", "message": str(e)}), 500


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
            "🤖 Simulasyon AL/SAT bildirimleri bu kanala gelecek."
        )
        if ok:
            return jsonify({"status": "success", "message": "Test mesaji gonderildi. Telegram'ı kontrol edin."})
        return jsonify({"status": "error", "message": "Gonderim basarisiz. Token/Chat ID'yi ve botun sohbeti baslattigini kontrol edin."}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/simulation/send_telegram', methods=['POST'])
def api_simulation_send_telegram():
    try:
        data = request.json
        date_str = data.get('date')
        if not date_str:
            return jsonify({"status": "error", "message": "Date is required"}), 400
            
        sim_res = api_simulation_daily_pnl().json
        if sim_res.get("status") != "success":
            return jsonify({"status": "error", "message": "Simülasyon hesaplanamadı"}), 500
            
        eq_log = sim_res.get("equity_curve", [])
        day_data = next((d for d in eq_log if d["date_str"] == date_str), None)
        
        if not day_data:
            return jsonify({"status": "error", "message": "Belirtilen tarih için simülasyon verisi bulunamadı"}), 404
            
        trades = [t for t in sim_res.get("trades", []) if t["date_str"] == date_str]
        
        # Telegram Mesajını Oluştur
        is_profit = day_data['daily_pnl'] >= 0
        icon = "🟢" if is_profit else "🔴"
        
        total_invested = sum([(t.get('shares',0) * t.get('entry_price',0)) for t in trades])
        pct = (day_data['daily_pnl'] / total_invested * 100) if total_invested > 0 else 0
        
        msg = (
            f"🧪 <b>ORACLE SİMÜLASYON RAPORU</b> 🧪\n"
            f"📅 <b>Tarih:</b> {date_str}\n"
            f"📊 <b>İşlem Gören Hisse Sayısı:</b> {len(trades)}\n"
            f"💰 <b>Yatırılan Tutar:</b> {total_invested:,.2f} ₺\n"
            f"{icon} <b>Günlük K/Z:</b> {day_data['daily_pnl']:,.2f} ₺ (%{pct:.2f})\n\n"
            f"📋 <b>GÜN İÇİ İŞLEMLER:</b>\n"
        )
        
        for t in trades:
            pnl = float(t.get('pnl', t.get('pnl_val', 0)) or 0)
            pnl_pct = float(t.get('pnl_pct', 0) or 0)
            t_icon = "🟢" if pnl >= 0 else "🔴"
            msg += (
                f"▪️ <b>#{t.get('symbol', t.get('ticker', '-'))}</b> - {t.get('shares', t.get('quantity', 0))} Lot\n"
                f"   └ <i>Alış:</i> {float(t.get('buy_price', t.get('entry_price', 0)) or 0):.2f} ₺ ⏱️ {t.get('buy_time', '10:15')}\n"
                f"   └ <i>Satış:</i> {float(t.get('sell_price', t.get('exit_price', 0)) or 0):.2f} ₺ ⏱️ {t.get('sell_time', 'Zirve')}\n"
                f"   └ <i>K/Z:</i> {t_icon} {pnl:,.2f} ₺ (%{pnl_pct:.2f})\n\n"
            )
            
        msg += f"🤖 <i>VarantRadar Pro Simülasyon Motoru</i>"
        
        from services.notification_manager import NotificationManager
        notif = NotificationManager()
        if not notif.telegram_chat_id or "BURAYA_" in str(notif.telegram_token):
            return jsonify({"status": "error", "message": "Telegram ayarları yapılandırılmamış."}), 400
            
        success = notif.send_telegram_message(msg)
        if success:
            return jsonify({"status": "success", "message": "Rapor Telegram'a gönderildi."})
        else:
            return jsonify({"status": "error", "message": "Telegram'a gönderilirken bir hata oluştu."}), 500
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500



import time
XU100_CACHE = {"change": 0.0, "last_updated": 0}

def get_xu100_change():
    global XU100_CACHE
    now = time.time()
    if now - XU100_CACHE['last_updated'] > 300: # 5 min cache
        try:
            import yfinance as yf
            hist = yf.Ticker('XU100.IS').history(period='5d')
            if len(hist) >= 2:
                c1 = hist['Close'].iloc[-2]
                c2 = hist['Close'].iloc[-1]
                chg = ((c2 - c1) / c1) * 100
                XU100_CACHE['change'] = chg
                XU100_CACHE['last_updated'] = now
        except Exception as e:
            pass
    return XU100_CACHE['change']




@app.route('/api/v8/learning/outcomes', methods=['GET'])
def api_v8_learning_outcomes():
    try:
        from v8_engine.database import V8Database
        conn = V8Database.get_connection()
        cursor = conn.cursor()
        
        # Sinyalleri ve sonuclarini JOIN ile getir
        query = '''
            SELECT s.signal_id, s.symbol, s.timestamp, s.entry_price, s.score, s.status, s.market_regime,
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
        for r in rows:
            outcomes.append({
                "signal_id": r["signal_id"],
                "symbol": r["symbol"],
                "timestamp": r["timestamp"],
                "entry_price": r["entry_price"],
                "score": r["score"],
                "status": r["status"],
                "market_regime": r["market_regime"],
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
                "mfe": r["mfe"],
                "mae": r["mae"],
                "final_result": r["final_result"]
            })
            
        conn.close()
        return jsonify({"status": "success", "data": outcomes})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/v8/radar/breakout', methods=['GET'])
def api_v8_radar_breakout():
    all_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
    breakout_list = []
    
    for sym, data in all_stats.items():
        bo = data.get("v8_breakout")
        if bo and bo.get("is_breakout"):
            bo["symbol"] = sym
            bo["price"] = data.get("Daily_Close", 0.0)
            bo["change_pct"] = data.get("Change_Pct", 0.0)
            bo["volume"] = data.get("Volume", 0)
            bo["entry_status"] = data.get("v8_execution", {}).get("entry_status", "UNKNOWN")
            bo["entry_reasons"] = data.get("v8_execution", {}).get("reasons", [])
            breakout_list.append(bo)
            
    # Siralama: Oncelikle kaliteli kirilimlar
    breakout_list = sorted(breakout_list, key=lambda x: x.get("breakout_score", 0) - x.get("fakeout_risk", 0), reverse=True)
    return jsonify({"status": "success", "data": breakout_list})

@app.route('/api/v8/radar/discovery', methods=['GET'])
def api_v8_radar_discovery():
    all_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
    discovery_list = []
    
    for sym, data in all_stats.items():
        disc = data.get("v8_discovery")
        if disc and disc.get("state") in ["READY", "PREPARING", "WATCH"]:
            # Combine some essential pricing data
            disc["symbol"] = sym
            disc["price"] = data.get("Daily_Close", 0.0)
            disc["change_pct"] = data.get("Change_Pct", 0.0)
            disc["volume"] = data.get("Volume", 0)
            discovery_list.append(disc)
            
    # Puanlara gore sirala
    discovery_list = sorted(discovery_list, key=lambda x: x.get("preparation_score", 0), reverse=True)
    return jsonify({"status": "success", "data": discovery_list})

@app.route('/api/v8/market/regime', methods=['GET'])
def api_v8_market_regime():
    regime_data = GLOBAL_DASHBOARD_CACHE.get("v8_market_regime", {"regime": "UNKNOWN", "score": 50.0, "xu100_trend": 0.0})
    return jsonify(regime_data)

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
        return jsonify({"status": "error", "message": str(e)}), 500


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
        return jsonify({"status": "error", "message": str(e), "trace": traceback.format_exc()}), 500


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
        return jsonify({"status": "error", "message": str(e)}), 500


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
        return jsonify({"status": "error", "message": str(e), "trace": traceback.format_exc()}), 500


if __name__ == "__main__":

    print("[SYSTEM] VarantRadar Pro Web Server Baslatiliyor...")

    port = int(os.environ.get("PORT", 5000))

    # Flask debug restart yapınca ikinci thread açılmasın
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        t = threading.Thread(
            target=background_scanner,
            daemon=True
        )
        t.start()
        # Simülasyon sürekli arka plan döngüsü (AL/SAT anında Telegram bildirimi)
        t_sim = threading.Thread(target=simulation_loop, daemon=True, name="simulation-loop")
        t_sim.start()
        try:
            start_live_data_collector()
        except Exception as e:
            print(f"[LIVE DATA] Baslatilamadi: {e}")
        try:
            from services.detective_engine import start_background_loop
            start_background_loop()
        except Exception as e:
            print(f"[DEDEKTIF] Arka plan baslatilamadi: {e}")

    render_url = os.getenv("RENDER_EXTERNAL_URL")

    if render_url:
        print(f"[URL] Render URL: {render_url}")
    else:
        print(f"[URL] Local URL: http://127.0.0.1:{port}")

    app.run(
        host="0.0.0.0",
        port=port
    )



