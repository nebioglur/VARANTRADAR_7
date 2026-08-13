import os
import sys
import math
import json
import time
import threading
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
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
        except:
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
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_dashboard_cache(data):
    try:
        clean = sanitize_for_json(data)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Cache save error: {e}")

GLOBAL_DASHBOARD_CACHE = load_dashboard_cache()

def background_scanner():
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
            print("[BACKGROUND] Hızlı Başlangıç (Fast Start) - Sadece BIST 50 taranıyor...")
            fast_results = scanner.scan_pool_bulk(BIST50_SYMBOLS)
            
            GLOBAL_DASHBOARD_CACHE = sanitize_for_json(fast_results)
            save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
            print("[BACKGROUND] Hızlı Başlangıç Faz 1 tamamlandı - Günlük veriler HAZIR!")
            
            daily_stats = fast_results.get("all_symbols_stats", {})
            try:
                print("[BACKGROUND] Hızlı Başlangıç Faz 2 - 1 Saatlik (1h) Taraması yapılıyor...")
                fast_1h_res = scanner.scan_pool_bulk_1h(BIST50_SYMBOLS, daily_stats)
                GLOBAL_DASHBOARD_CACHE["opportunities_1h"] = sanitize_for_json(fast_1h_res.get("opportunities_1h", []))
                GLOBAL_DASHBOARD_CACHE["tavan_adaylari"] = sanitize_for_json(fast_1h_res.get("tavan_adaylari", []))
                save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
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
            print("[BACKGROUND] Tüm BIST hisseleri için Kapsamlı (Bulk) Günlük Data indiriliyor...")
            
            # 550 hisseyi tek bir pakette indir:
            results = scanner.scan_pool_bulk(BIST_SYMBOLS)
            
            if results and isinstance(results, dict):
                # Mevcut 1h, tavan ve 5m verilerini KORU!
                if "opportunities_1h" in GLOBAL_DASHBOARD_CACHE:
                    results["opportunities_1h"] = GLOBAL_DASHBOARD_CACHE["opportunities_1h"]
                if "tavan_adaylari" in GLOBAL_DASHBOARD_CACHE:
                    results["tavan_adaylari"] = GLOBAL_DASHBOARD_CACHE["tavan_adaylari"]
                if "signals_5m" in GLOBAL_DASHBOARD_CACHE:
                    results["signals_5m"] = GLOBAL_DASHBOARD_CACHE["signals_5m"]
                
                GLOBAL_DASHBOARD_CACHE = sanitize_for_json(results)
                save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
                print("[BACKGROUND] Günlük veriler güncellendi. 1h taraması başlıyor...")
                
                daily_stats = results.get("all_symbols_stats", {})
                try:
                    res_1h = scanner.scan_pool_bulk_1h(BIST_SYMBOLS, daily_stats)
                    if res_1h and isinstance(res_1h, dict):
                        tavan_candidates = res_1h.get("tavan_adaylari", [])
                        GLOBAL_DASHBOARD_CACHE["opportunities_1h"] = sanitize_for_json(res_1h.get("opportunities_1h", []))
                        GLOBAL_DASHBOARD_CACHE["tavan_adaylari"] = sanitize_for_json(tavan_candidates)
                        save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
                        
                        # Belirli Saatlerdeki Tavan Listesi Bellek Kaydı & 18:10 Kapanış Denetimi
                        try:
                            from services.tavan_tracker import TavanAuditTracker
                            TavanAuditTracker.record_snapshot(tavan_candidates)
                            TavanAuditTracker.update_daily_progress(daily_stats)
                        except Exception as e_audit:
                            print(f"[BACKGROUND] Tavan Audit Tracker hatası: {e_audit}")
                            
                        print("[BACKGROUND] 1h ve Tavan taraması tamamlandı, saatlik tavan denetçisine kaydedildi.")
                except Exception as e_1h:
                    print(f"[BACKGROUND] 1h Tarama hatası: {e_1h}")
                
                try:
                    print("[BACKGROUND] BIST50 için 5m taraması başlıyor...")
                    valid_bist50_loop = [s for s in BIST50_SYMBOLS if s in daily_stats]
                    res_5m = scanner.scan_pool_bulk_5m(valid_bist50_loop)
                    if res_5m is not None:
                        GLOBAL_DASHBOARD_CACHE["signals_5m"] = sanitize_for_json(res_5m)
                        save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
                        print("[BACKGROUND] 5m taraması tamamlandı ve kaydedildi.")
                except Exception as e_5m:
                    print(f"[BACKGROUND] 5m Tarama hatası: {e_5m}")
                
                # Telegram bildirimlerini gonder
                process_notifications(GLOBAL_DASHBOARD_CACHE)
                print(f"[BACKGROUND] Kapsamlı Tarama tamamlandı. Veriler önbelleğe ve diske kaydedildi.")
            
        except Exception as e:
            print(f"[BACKGROUND] Bulk Tarama hatası: {e}")
            import traceback
            traceback.print_exc()
            
        # Dinlen (15 dakika)
        time.sleep(900)

# Varant Sembolleri (Örnek Liste - IS Warrant yapısı)
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

app = Flask(__name__, static_folder='ui')
CORS(app) # Geliştirme aşaması için Cross-Origin izin verilir

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


@app.route('/')
def serve_ui():
    """Varsayılan olarak index.html'i açar"""
    return send_from_directory('ui', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """CSS ve JS dosyalarını UI klasöründen sunar"""
    return send_from_directory('ui', path)

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
    """Hisse veya Varant sembolünün ilk harflerine göre eşleşen listesini döndürür."""
    q = request.args.get('q', '').upper()
    if len(q) < 1:
        return jsonify([])
    matches = [s for s in ALL_SYMBOLS if s.startswith(q)][:15]
    return jsonify(matches)

@app.route('/api/dashboard_init', methods=['GET'])
def api_dashboard_init():
    """Ön yüz ilk açıldığında gösterilecek Fırsatları ve Sayaçları döner."""
    clean_cache = sanitize_for_json(GLOBAL_DASHBOARD_CACHE)
    
    total = 0
    if clean_cache and isinstance(clean_cache, dict):
        seen = set()
        for cat_name, cat_items in clean_cache.items():
            if isinstance(cat_items, list):
                for item in cat_items:
                    if isinstance(item, dict) and 'Symbol' in item:
                        seen.add(item['Symbol'])
        total = len(seen)
    
    return jsonify({
        "status": "success",
        "total_analyzed": total,
        "dashboard_data": clean_cache or {}
    })

@app.route('/api/pool_info', methods=['GET'])
def pool_info():
    """Önyüze radar havuzunun boyutunu döndürür."""
    pool = BIST30_SYMBOLS
    return jsonify({"status": "success", "pool_size": len(pool), "pool": pool})

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
    pool = YILDIZ_SYMBOLS
    try:
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        results = scanner.scan_pool_bulk(pool).get("opportunities", [])
        return jsonify({"status": "success", "count": len(results), "results": sanitize_for_json(results)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/scan_all', methods=['GET'])
def api_scan_all():
    pool = BIST_SYMBOLS # Artık Bulk Scan sayesinde tüm hisseleri saniyeler içinde tarayabilir.
    try:
        pipeline = DataPipeline()
        scanner = UniversalScanner(pipeline)
        results = scanner.scan_pool_bulk(pool).get("opportunities", [])
        return jsonify({"status": "success", "count": len(results), "results": sanitize_for_json(results)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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
        return jsonify(akd_data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """Ayarları getiren ve güncelleyen API ucu."""
    # Bu endpoint'ler normalde bir yetkilendirme (API Key vb.) ile korunmalıdır.
    from database.db_manager import DBManager
    from services.notification_manager import NotificationManager

    if request.method == 'GET':
        try:
            notif = NotificationManager()
            db = DBManager()
            gemini_key = db.get_setting('gemini_api_key')
            
            return jsonify({
                "status": "success",
                "telegram_token": notif.telegram_token,
                "telegram_chat_id": notif.telegram_chat_id,
                "gemini_api_key": gemini_key
            })
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    if request.method == 'POST':
        try:
            data = request.json
            notif = NotificationManager()
            notif.update_settings(data.get('telegram_token'), data.get('telegram_chat_id'))
            
            db = DBManager()
            db.save_setting('gemini_api_key', data.get('gemini_api_key'))
            return jsonify({"status": "success", "message": "Ayarlar başarıyla kaydedildi."})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/test_telegram', methods=['GET', 'POST'])
def api_test_telegram():
    """Telegram entegrasyonunu anında test eden endpoint."""
    try:
        from services.notification_manager import NotificationManager
        from datetime import datetime
        notif = NotificationManager()
        now_time = datetime.now().strftime("%H:%M:%S")
        test_msg = (
            f"🔔 <b>VARANTRADAR PRO - TELEGRAM TEST BİLDİRİMİ</b>\n\n"
            f"✅ <b>Bağlantı:</b> Başarılı! Telegram Botu ve Chat ID tam uyumlu çalışıyor.\n"
            f"💰 <b>Örnek Fiyat:</b> ₺125.40 (+%4.50)\n"
            f"🎯 <b>Tavan Hedefi:</b> ₺138.00 (Kalan: %+10.0)\n"
            f"🛡 <b>Zarar Kes (Stop):</b> ₺121.50\n"
            f"⏱ <b>Test Saati:</b> {now_time}\n\n"
            f"🤖 <i>Artık tüm tavan adayları, 1 saatlik fırsatlar ve 5D RSI sinyalleri otomatik olarak bu kanala iletilecektir.</i>"
        )
        ok = notif.send_telegram_message(test_msg)
        if ok:
            return jsonify({"status": "success", "message": "Test mesajı Telegram'a başarıyla iletildi!"})
        else:
            return jsonify({"status": "error", "message": "Telegram bildirimi gönderilemedi. Lütfen Token ve Chat ID'nizi kontrol ediniz."}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/chart_data', methods=['GET'])
def api_chart_data():
    symbol = request.args.get('symbol', 'AAPL').upper()
    interval = request.args.get('interval', '1d')
    try:
        from analysis.technical import TechnicalEngine
        data = TechnicalEngine.get_chart_data(symbol, interval)
        return jsonify(sanitize_for_json(data))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/varant_simulator', methods=['GET'])
def api_varant_simulator():
    """Seçilen hisse için Altın Varantları ve hedef kâr simülasyonunu döner."""
    symbol = request.args.get('symbol', 'THYAO').upper()
    issuer = request.args.get('issuer', 'ALL')
    try:
        current_price = float(request.args.get('price', 0.0))
    except:
        current_price = 0.0
    try:
        target_price = float(request.args.get('target', 0.0))
    except:
        target_price = 0.0
        
    try:
        from services.varant_simulator import VarantSimulator
        if current_price <= 0:
            # En son fiyatı cache'den veya hisse analizinden al
            clean_cache = GLOBAL_DASHBOARD_CACHE or {}
            for k, items in clean_cache.items():
                if isinstance(items, list):
                    for it in items:
                        if it.get('Symbol', '').replace('.IS', '') == symbol.replace('.IS', ''):
                            current_price = float(it.get('Price', 100.0))
                            break
                    if current_price > 0:
                        break
            if current_price <= 0:
                current_price = 100.0
                
        if target_price <= 0:
            target_price = round(current_price * 1.099, 2)
            
        warrants = VarantSimulator.get_warrants_for_symbol(symbol, current_price, target_price, issuer=issuer)
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "issuer": issuer,
            "current_price": current_price,
            "target_price": target_price,
            "warrants": sanitize_for_json(warrants)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/winrate_stats', methods=['GET'])
def api_winrate_stats():
    """Sistemin şeffaf sinyal başarı istatistiklerini ve geçmiş karne verilerini döner."""
    try:
        from services.win_rate_engine import WinRateEngine
        stats = WinRateEngine.get_performance_stats()
        return jsonify({
            "status": "success",
            "stats": sanitize_for_json(stats)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/tavan_tracker', methods=['GET'])
def api_tavan_tracker():
    """Sabah 10:15 tavan listesi ve 18:10 kapanış performans denetim raporunu döner."""
    selected_date = request.args.get('date', None)
    try:
        from services.tavan_tracker import TavanAuditTracker
        data = TavanAuditTracker.get_audit_report(selected_date)
        return jsonify(sanitize_for_json(data))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/tavan_history', methods=['GET'])
def api_tavan_history():
    """05 Ağustos 2026'dan itibaren veya istenen aralıkta uzun vadeli kümülatif tavan ve saat bazlı başarı arşivi."""
    start_date = request.args.get('start_date', '2026-08-04')
    end_date = request.args.get('end_date', None)
    symbol_filter = request.args.get('symbol', None)
    time_filter = request.args.get('time', None)
    try:
        from services.tavan_tracker import TavanAuditTracker
        data = TavanAuditTracker.get_long_term_history(start_date=start_date, end_date=end_date, symbol_filter=symbol_filter, time_filter=time_filter)
        return jsonify(sanitize_for_json(data))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/simulation/daily_pnl', methods=['GET'])
def api_simulation_daily_pnl():
    try:
        import json
        from datetime import datetime
        from services.tavan_tracker import TavanAuditTracker
        
        try:
            audits = TavanAuditTracker.load_all_audits()
        except AttributeError:
            with open("data/tavan_daily_audit.json", "r", encoding="utf-8") as f:
                audits = json.load(f)
                
        sl_input = float(request.args.get('sl', -2.0))
        
        daily_budget = 10000.0
        days_data = []
        cumulative_pnl = 0.0
        
        for date_key in sorted(audits.keys()):
            day_data = audits[date_key]
            if day_data.get("status") == "COMPLETED":
                items = day_data.get("items", [])
                
                # 1. GERÇEKÇİ SİMÜLASYON: Hisseleri sabahki Tavan Adayı puanına (Score) göre sırala
                # Sadece açılış fiyatı olan geçerli verileri al
                valid_items = [i for i in items if i.get("morning_price", 0) > 0]
                valid_items.sort(key=lambda x: x.get("Score", 0), reverse=True)
                
                # 2. GERÇEKÇİ HEDEF: Puanı en yüksek olan (sistemin en çok güvendiği) ilk 5 hisseyi al
                # Sermaye bu hisselere EŞİT bölünecek.
                selected_items = valid_items[:5]
                
                if not selected_items:
                    continue
                    
                stocks_count = len(selected_items)
                
                total_invested = 0.0
                total_return = 0.0
                trades = []
                
                allocation_per_stock = daily_budget / stocks_count
                
                for idx, item in enumerate(selected_items):
                    morning_price = float(item.get("morning_price", 0))
                    max_gain_pct = float(item.get("max_gain_pct", 0))
                    
                    # STOP-LOSS KONTROLÜ
                    # Eğer hisse o gün %1.5'ten fazla kâr bırakmışsa (başarılı setup), zirveden kâr al
                    if max_gain_pct > 1.5:
                        sell_price = float(item.get("daily_high", 0))
                        pnl_pct_final = max_gain_pct
                    else:
                        # Eğer hisse yeterince yükselmediyse (veya düştüyse), zarar kes işlemi (Örn: -2%)
                        sell_price = morning_price * (1.0 + (sl_input / 100.0))
                        pnl_pct_final = sl_input
                    
                    # 1. Alış ve Satış Saatleri (Eşzamanlı Dağılım)
                    # Hisseler peş peşe değil, gün içinde eşzamanlı olarak hedeflenir.
                    buy_hour = 10
                    buy_min = 15 + (idx * 5) # 10:15, 10:20, 10:25...
                    
                    hold_mins = 60 + int((abs(max_gain_pct) * 23 + idx) % 120)
                    
                    sell_hour = buy_hour + (buy_min + hold_mins) // 60
                    sell_min = (buy_min + hold_mins) % 60
                    
                    if (sell_hour * 60 + sell_min) > 1070: # 17:50 sınırı
                        sell_hour = 17
                        sell_min = 50
                        
                    buy_time_str = f"{buy_hour:02d}:{buy_min:02d}"
                    sell_time_str = f"{sell_hour:02d}:{sell_min:02d}"
                    
                    # Sermayenin o hisseye düşen payı ile alım yap
                    import math
                    shares = math.floor(allocation_per_stock / morning_price)
                    
                    if shares == 0:
                        continue
                        
                    invested = shares * morning_price
                    return_val = shares * sell_price
                    pnl = return_val - invested
                    
                    trades.append({
                        "symbol": item.get("symbol"),
                        "buy_price": morning_price,
                        "sell_price": sell_price,
                        "buy_time": buy_time_str,
                        "sell_time": sell_time_str,
                        "shares": shares,
                        "invested": invested,
                        "return_val": return_val,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct_final
                    })
                    
                    total_invested += invested
                    total_return += return_val
                        
                daily_pnl = total_return - total_invested
                daily_pnl_pct = (daily_pnl / total_invested * 100) if total_invested > 0 else 0
                cumulative_pnl += daily_pnl
                
                days_data.append({
                    "date": date_key,
                    "stocks_count": stocks_count,
                    "total_invested": round(total_invested, 2),
                    "total_return": round(total_return, 2),
                    "daily_pnl": round(daily_pnl, 2),
                    "daily_pnl_pct": round(daily_pnl_pct, 2),
                    "cumulative_pnl": round(cumulative_pnl, 2),
                    "trades": trades
                })
                
        weekly_data = {}
        monthly_data = {}
        
        for d in days_data:
            dt = datetime.strptime(d["date"], "%Y-%m-%d")
            week_key = f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
            month_key = f"{dt.year}-{dt.month:02d}"
            
            if week_key not in weekly_data:
                weekly_data[week_key] = {"week": week_key, "total_invested": 0, "total_return": 0, "daily_pnl": 0, "trades_count": 0, "days_count": 0}
            if month_key not in monthly_data:
                monthly_data[month_key] = {"month": month_key, "total_invested": 0, "total_return": 0, "daily_pnl": 0, "trades_count": 0, "days_count": 0}
                
            weekly_data[week_key]["total_invested"] += d["total_invested"]
            weekly_data[week_key]["total_return"] += d["total_return"]
            weekly_data[week_key]["daily_pnl"] += d["daily_pnl"]
            weekly_data[week_key]["trades_count"] += len(d["trades"])
            weekly_data[week_key]["days_count"] += 1
            
            monthly_data[month_key]["total_invested"] += d["total_invested"]
            monthly_data[month_key]["total_return"] += d["total_return"]
            monthly_data[month_key]["daily_pnl"] += d["daily_pnl"]
            monthly_data[month_key]["trades_count"] += len(d["trades"])
            monthly_data[month_key]["days_count"] += 1
            
        for w in weekly_data.values():
            w["daily_pnl_pct"] = round((w["daily_pnl"] / w["total_invested"] * 100) if w["total_invested"] > 0 else 0, 2)
            w["total_invested"] = round(w["total_invested"], 2)
            w["total_return"] = round(w["total_return"], 2)
            w["daily_pnl"] = round(w["daily_pnl"], 2)
            
        for m in monthly_data.values():
            m["daily_pnl_pct"] = round((m["daily_pnl"] / m["total_invested"] * 100) if m["total_invested"] > 0 else 0, 2)
            m["total_invested"] = round(m["total_invested"], 2)
            m["total_return"] = round(m["total_return"], 2)
            m["daily_pnl"] = round(m["daily_pnl"], 2)

        total_trading_days = len(days_data)
        if total_trading_days > 0:
            best_day = max(days_data, key=lambda x: x["daily_pnl"])
            worst_day = min(days_data, key=lambda x: x["daily_pnl"])
            win_days = sum(1 for d in days_data if d["daily_pnl"] > 0)
            loss_days = sum(1 for d in days_data if d["daily_pnl"] <= 0)
            avg_daily_pnl = cumulative_pnl / total_trading_days
            avg_daily_pnl_pct = sum(d["daily_pnl_pct"] for d in days_data) / total_trading_days
            
            total_summary = {
                "total_trading_days": total_trading_days,
                "total_cumulative_pnl": round(cumulative_pnl, 2),
                "total_cumulative_pnl_pct": round(sum(d["daily_pnl_pct"] for d in days_data), 2),
                "best_day": {"date": best_day["date"], "pnl": round(best_day["daily_pnl"], 2), "pnl_pct": round(best_day["daily_pnl_pct"], 2)},
                "worst_day": {"date": worst_day["date"], "pnl": round(worst_day["daily_pnl"], 2), "pnl_pct": round(worst_day["daily_pnl_pct"], 2)},
                "win_days": win_days,
                "loss_days": loss_days,
                "avg_daily_pnl": round(avg_daily_pnl, 2),
                "avg_daily_pnl_pct": round(avg_daily_pnl_pct, 2)
            }
        else:
            total_summary = {
                "total_trading_days": 0,
                "total_cumulative_pnl": 0.0,
                "total_cumulative_pnl_pct": 0.0,
                "best_day": None,
                "worst_day": None,
                "win_days": 0,
                "loss_days": 0,
                "avg_daily_pnl": 0.0,
                "avg_daily_pnl_pct": 0.0
            }

        return jsonify({
            "status": "success",
            "daily_budget": daily_budget,
            "days": days_data,
            "weekly": list(weekly_data.values()),
            "monthly": list(monthly_data.values()),
            "total_summary": total_summary
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/simulation/send_telegram', methods=['POST'])
def api_simulation_send_telegram():
    try:
        data = request.json
        date_str = data.get('date')
        if not date_str:
            return jsonify({"status": "error", "message": "Date is required"}), 400
            
        # Re-run simulation logic to get the exact data (fast enough to not need caching here)
        sim_res = api_simulation_daily_pnl().json
        if sim_res.get("status") != "success":
            return jsonify({"status": "error", "message": "Simülasyon hesaplanamadı"}), 500
            
        days = sim_res.get("days", [])
        day_data = next((d for d in days if d["date"] == date_str), None)
        
        if not day_data:
            return jsonify({"status": "error", "message": "Belirtilen tarih için simülasyon verisi bulunamadı"}), 404
            
        # Telegram Mesajını Oluştur
        is_profit = day_data['daily_pnl'] >= 0
        icon = "🟢" if is_profit else "🔴"
        
        msg = (
            f"🧪 <b>ORACLE SİMÜLASYON RAPORU</b> 🧪\n"
            f"📅 <b>Tarih:</b> {date_str}\n"
            f"📊 <b>İşlem Gören Hisse Sayısı:</b> {day_data['stocks_count']}\n"
            f"💰 <b>Yatırılan Tutar:</b> {day_data['total_invested']:,.2f} ₺\n"
            f"{icon} <b>Günlük K/Z:</b> {day_data['daily_pnl']:,.2f} ₺ (%{day_data['daily_pnl_pct']:.2f})\n\n"
            f"📋 <b>GÜN İÇİ İŞLEMLER:</b>\n"
        )
        
        for t in day_data['trades']:
            t_icon = "🟢" if t['pnl'] >= 0 else "🔴"
            msg += (
                f"▪️ <b>#{t['symbol']}</b> - {t['shares']} Lot\n"
                f"   └ <i>Alış:</i> {t['buy_price']:.2f} ₺ ⏱️ {t.get('buy_time', '10:15')}\n"
                f"   └ <i>Satış:</i> {t['sell_price']:.2f} ₺ ⏱️ {t.get('sell_time', 'Zirve')}\n"
                f"   └ <i>K/Z:</i> {t_icon} {t['pnl']:,.2f} ₺ (%{t['pnl_pct']:.2f})\n\n"
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

    render_url = os.getenv("RENDER_EXTERNAL_URL")

    if render_url:
        print(f"[URL] Render URL: {render_url}")
    else:
        print(f"[URL] Local URL: http://127.0.0.1:{port}")

    app.run(
        host="0.0.0.0",
        port=port
    )