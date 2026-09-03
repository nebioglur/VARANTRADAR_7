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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
            print(f"[Server] load_stats Error: {e}")
            return {"total_analyzed": 0}
    return {"total_analyzed": 0}

def save_stats(stats):
    try:
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f)
    except Exception as e:
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
        print(f"Stats save error: {e}")

CACHE_FILE = "dashboard_cache.json"

def load_dashboard_cache():
    if os.path.exists(CACHE_FILE):
        try:
            from datetime import datetime
            import time
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                today_str = datetime.now().strftime("%Y-%m-%d")
                cache_date = data.get("cache_date")
                if cache_date:
                    if cache_date != today_str:
                        print(f"[Server] Eski günün cache dosyası reddedildi ({cache_date} != {today_str}).")
                        return {}
                else:
                    mtime = os.path.getmtime(CACHE_FILE)
                    if time.time() - mtime > 1800:
                        print("[Server] Cache tarihi yok ve dosya 30 dakikadan eski. Reddedildi.")
                        return {}
                return data
        except Exception as e:
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
            print(f"[Server] load_dashboard_cache Error: {e}")
            return {}
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
        print(f"[GITHUB ERROR] {e}")

def save_dashboard_cache(data):
    try:
        clean = sanitize_for_json(data)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)
    except Exception as e:
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
        print(f"Cache save error: {e}")

GLOBAL_DASHBOARD_CACHE = load_dashboard_cache()


# === VERITABANI TABLOLARINI OLUŞTUR (Simülasyon Motoru için) ===
try:
    from services.trade_database import init_db
    init_db()
    print("[SERVER] Simülasyon veritabanı tabloları hazır.")
except Exception as e_init:
    print(f"[SERVER] init_db hatası: {e_init}")

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
            from datetime import datetime
            fast_results["cache_date"] = datetime.now().strftime("%Y-%m-%d")
            
            GLOBAL_DASHBOARD_CACHE = sanitize_for_json(fast_results)
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
            print(f"[BACKGROUND] Hızlı Başlangıç Hatası: {e}")
            import traceback
            traceback.print_exc()

    while True:
        try:
            print("[BACKGROUND] Tüm BIST hisseleri için Kapsamlı (Bulk) Günlük Data indiriliyor...")
            
            # 550 hisseyi tek bir pakette indir:
            results = scanner.scan_pool_bulk(BIST_SYMBOLS)
            from datetime import datetime
            if isinstance(results, dict): results["cache_date"] = datetime.now().strftime("%Y-%m-%d")
            
            from datetime import datetime
            today_str = datetime.now().strftime("%Y-%m-%d")
            if GLOBAL_DASHBOARD_CACHE.get("cache_date", today_str) != today_str:
                print("[BACKGROUND] Yeni gun tespit edildi. Eski bellekteki veriler temizleniyor.")
                GLOBAL_DASHBOARD_CACHE = {}

            if results and isinstance(results, dict):
                # Mevcut 1h, tavan ve 5m verilerini KORU!
                if "opportunities_1h" in GLOBAL_DASHBOARD_CACHE:
                    results["opportunities_1h"] = GLOBAL_DASHBOARD_CACHE["opportunities_1h"]
                if "tavan_adaylari" in GLOBAL_DASHBOARD_CACHE:
                    results["tavan_adaylari"] = GLOBAL_DASHBOARD_CACHE["tavan_adaylari"]
                if "stay_away_1h" in GLOBAL_DASHBOARD_CACHE:
                    results["stay_away_1h"] = GLOBAL_DASHBOARD_CACHE["stay_away_1h"]
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
                        GLOBAL_DASHBOARD_CACHE["stay_away_1h"] = sanitize_for_json(res_1h.get("stay_away_1h", []))
                        save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
                        
                        # Belirli Saatlerdeki Tavan Listesi Bellek Kaydı & 18:10 Kapanış Denetimi
                        try:
                            from services.tavan_tracker import TavanAuditTracker
                            TavanAuditTracker.record_snapshot(tavan_candidates)
                            TavanAuditTracker.update_daily_progress(daily_stats)
                            
                            # YENİ MİMARİ: SQLite'a sinyalleri ve market datasını kaydet
                            from services.market_data import MarketDataManager
                            from services.simulation_engine import SimulationEngine
                            from datetime import datetime
                            d_str = datetime.now().strftime("%Y-%m-%d")
                            MarketDataManager.record_signals(d_str, tavan_candidates)
                            MarketDataManager.fetch_and_store_intraday(d_str)
                            
                            # Günlük simülasyonu çalıştır
                            sim = SimulationEngine()
                            sim.run_daily_simulation(d_str)
                            
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
                                                c.execute("SELECT * FROM trades WHERE date_str=?", (d_str,))
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
        time.sleep(900)

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
CORS(app)

# ============ SESSION AUTH (GÜVENLİK) ============
import os
from flask import request, Response, session, redirect, jsonify, render_template_string

app.secret_key = os.environ.get('SECRET_KEY', 'varant_pro_ultra_secret_2026_xyz')
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'radar123')

@app.before_request
def require_auth():
    if request.method == 'OPTIONS': return
    
    allowed = ['/login', '/logout']
    if request.path in allowed: return
    
    # Allow static assets for login page
    if request.path.endswith('.css') or request.path.endswith('.js') or request.path.endswith('.png') or request.path.endswith('.woff2'):
        return

    if not session.get('logged_in'):
        if request.path.startswith('/api/'):
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USER and request.form.get('password') == ADMIN_PASS:
            session['logged_in'] = True
            return redirect('/')
        else:
            error = "Hatalı kullanıcı adı veya şifre!"
            
    # Send login.html but inject error if any
    try:
        with open('ui/login.html', 'r', encoding='utf-8') as f:
            html = f.read()
            if error:
                html = html.replace('<!-- ERROR_PLACEHOLDER -->', f'<div class="error-msg">{error}</div>')
            return html
    except:
        return "login.html bulunamadi", 404

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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


@app.route("/")
def index():
    response = make_response(send_from_directory("ui", "index.html"))
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
        "dashboard_data": clean_cache or {},\n        "xu100_change": get_xu100_change(),
        "last_updated": last_updated
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def api_health():
    """Tüm veri sağlayıcılarının sağlık durumunu döndürür."""
    try:
        pipeline = DataPipeline()
        health_report = pipeline.get_health_report()
        return jsonify({"status": "success", "data": health_report})
    except Exception as e:
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
            if score >= 80 and "YATAY" not in phase and "NEGATİF" not in phase and "UZAK DUR" not in phase:
                valid_signals.append(s)
                
        orders = []
        ideal_allocation = 3333.0 # Çelik kural: Sabit 100 TL risk, %3 stop = 3333 TL alım
        
        for s in valid_signals:
            morning_price = float(s.get('morning_price', 0))
            if morning_price <= 0: continue
            
            entry_price = morning_price * 1.0015 # %0.15 slipaj payı ile tahmini giriş
            shares = int(ideal_allocation // entry_price)
            if shares <= 0: continue
            
            ceiling = float(s.get('ceiling_target', entry_price * 1.10))
            
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/tavan_history', methods=['GET'])
def api_tavan_history():
    try:
        from services.tavan_tracker import TavanAuditTracker
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/winrate_stats', methods=['GET'])
def api_winrate_stats():
    try:
        from services.win_rate_engine import WinRateEngine
        stats = WinRateEngine.get_performance_stats()
        return jsonify({"status": "success", "stats": sanitize_for_json(stats)})
    except Exception as e:
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/tavan_tracker', methods=['GET'])
def api_tavan_tracker():
    try:
        from services.tavan_tracker import TavanAuditTracker
        date_str = request.args.get('date')
        res = TavanAuditTracker.get_audit_report(date_str)
        return jsonify(sanitize_for_json(res))
    except Exception as e:
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
            # Fetch daily equity log
            c.execute("SELECT * FROM equity_log ORDER BY date_str ASC")
            equity_rows = c.fetchall()
            equity_curve = [dict(row) for row in equity_rows]
            
            # Fetch closed trades
            c.execute("SELECT * FROM trades ORDER BY entry_time DESC LIMIT 100")
            trade_rows = c.fetchall()
            trades = [dict(row) for row in trade_rows]
            
            return jsonify({
                "status": "success",
                "equity_curve": sanitize_for_json(equity_curve),
        "trades": sanitize_for_json(trades)
            })
    except Exception as e:
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
        return jsonify({"status": "error", "message": str(e)})

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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
            pass
    return XU100_CACHE['change']
\n)

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
            err_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            try:
                from utils.sys_logger import log_error
                log_error("Background", f"Tarama Hatası: {err_str}")
            except:
                pass
        return jsonify({"status": "error", "message": str(e)}), 500
