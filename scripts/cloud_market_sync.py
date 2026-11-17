"""
VARANTRADAR PRO - CLOUD MARKET DATA ENGINE (GITHUB ACTIONS RUNNER)
==================================================================
Bu script GitHub Actions bulut ortamında (kesintisiz gigabit internet, sıfır ban)
çalışarak PythonAnywhere sunucusuna canlı piyasa verilerini ve 5m barları pompalar.

Çift Güvenceli Mimari:
1. Birincil Yol: Verdent Cloud tetiklemesi (/api/cron/sync_to_pa).
2. İkincil Yol (Failover): Verdent yanıt vermezse, doğrudan TradingView Bulk Scanner
   ile 625 BIST hissesi çekilir, açık pozisyonların 5m barları eklenir ve
   PythonAnywhere'e gzip ile doğrudan push yapılır.
"""

import os
import sys
import time
import json
import gzip
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

import requests

PA_URL = "https://varantradarpro.pythonanywhere.com"
VERDENT_URL = "https://varantradar-pro-8.verdent.app"
AUTH_TOKEN = "pro8_sync"

def get_istanbul_time():
    if ZoneInfo:
        return datetime.now(ZoneInfo("Europe/Istanbul"))
    return datetime.now()

def print_log(msg):
    t_str = get_istanbul_time().strftime("%H:%M:%S")
    print(f"[{t_str}] {msg}", flush=True)

def fetch_intraday_bars_safe(symbols, period="5d"):
    """GitHub runner ortamında öncelikli hisselerin 5m geçmiş barlarını çeker."""
    if not symbols:
        return []
    bars = []
    try:
        import yfinance as yf
        target = [s if s.endswith(".IS") else f"{s}.IS" for s in symbols][:30]
        data = yf.download(target, period=period, interval="5m", group_by='ticker', threads=True, progress=False)
        if data is None or data.empty:
            return []

        today_str = get_istanbul_time().strftime("%Y-%m-%d")

        for sym in target:
            try:
                df = data[sym] if (hasattr(data.columns, 'levels') and sym in data.columns.levels[0]) else data
                df = df.dropna(how='all')
                if df.empty:
                    continue
                for idx, row in df.iterrows():
                    ts = idx.isoformat()
                    d_str = ts[:10]
                    # Yalnızca son 2 günün barları
                    bars.append({
                        "date_str": d_str,
                        "timestamp": ts,
                        "symbol": sym,
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": float(row.get("Volume", 0)),
                        "source": "github_runner"
                    })
            except Exception:
                continue
    except Exception as e:
        print_log(f"[INTRADAY] yfinance çekme hatası: {e}")
    return bars

def push_to_pa(payload):
    """PythonAnywhere'e gzip sıkıştırma ile doğrudan yükler."""
    raw_bytes = json.dumps(payload).encode("utf-8")
    comp_bytes = gzip.compress(raw_bytes)
    resp = requests.post(
        f"{PA_URL}/api/system/push_market_data?token={AUTH_TOKEN}",
        data=comp_bytes,
        headers={"Content-Type": "application/json", "Content-Encoding": "gzip"},
        timeout=(15, 60)
    )
    return resp

def run_sync_cycle():
    now = get_istanbul_time()
    t_str = now.strftime("%H:%M:%S")
    today_str = now.strftime("%Y-%m-%d")

    # 1. Aşama: Verdent Cloud'dan tetikle
    verdent_ok = False
    try:
        r_v = requests.get(f"{VERDENT_URL}/api/cron/sync_to_pa", timeout=30)
        if r_v.status_code == 200:
            res_v = r_v.json()
            pa_res = res_v.get("pa_response", {})
            sym_count = pa_res.get("symbols_count", 0)
            if sym_count >= 500:
                print_log(f"[VERDENT OK] {sym_count} hisse başarıyla PA'ya aktarıldı.")
                verdent_ok = True
            else:
                print_log(f"[VERDENT UYARI] Verdent az hisse döndü ({sym_count}), failover devrede.")
    except Exception as e_v:
        print_log(f"[VERDENT BILGI] Verdent erişim hatası: {e_v}. Failover devrede.")

    if verdent_ok:
        return True

    # 2. Aşama (Failover): TradingView Bulk Scanner ile doğrudan çek ve PA'ya bas
    print_log("[FAILOVER DEVREDE] TradingView Bulk Scanner ile tüm BIST çekiliyor...")
    try:
        from data.providers.tradingview_provider import TradingViewBulkProvider
        tv = TradingViewBulkProvider()
        dash_data = tv.build_dashboard_data()
        stats = dash_data.get("all_symbols_stats", {})
        sym_count = len(stats)
        if sym_count < 100:
            print_log(f"[FAILOVER HATA] TradingView yetersiz hisse döndü: {sym_count}")
            return False

        # Açık pozisyonları ve sinyalleri çek
        cand_syms = [c.get("Symbol") for c in dash_data.get("tavan_adaylari", []) if c.get("Symbol")]
        
        # 5m barları topla
        bars = fetch_intraday_bars_safe(cand_syms[:20], period="3d")
        print_log(f"[FAILOVER DATA] {sym_count} hisse + {len(bars)} 5m bar hazırlandı. PA'ya yükleniyor...")

        payload = {
            "token": AUTH_TOKEN,
            "dashboard_data": dash_data,
            "xu100_change": dash_data.get("xu100_change"),
            "intraday_bars": bars
        }

        r_push = push_to_pa(payload)
        if r_push.status_code == 200:
            print_log(f"[FAILOVER SUCCESS] PythonAnywhere'e {sym_count} hisse başarıyla yüklendi! Yanıt: {r_push.json().get('status')}")
            return True
        else:
            print_log(f"[FAILOVER HATA] PA push yanıtı HTTP {r_push.status_code}: {r_push.text[:100]}")
            return False

    except Exception as e_fail:
        print_log(f"[FAILOVER HATA] Kritik failover hatası: {e_fail}")
        return False

def main():
    print_log("=" * 60)
    print_log("  VARANTRADAR PRO - CLOUD MARKET DATA ENGINE (GITHUB ACTIONS)")
    print_log(f"  Hedef: {PA_URL}")
    print_log("=" * 60)

    if "--once" in sys.argv:
        ok = run_sync_cycle()
        sys.exit(0 if ok else 1)

    max_loops = 90  # ~4.5 saatlik koşu
    loop = 0
    while loop < max_loops:
        loop += 1
        now = get_istanbul_time()
        h = now.hour
        m = now.minute

        # 18:35 TR sonrasında seans kapanışı
        if h > 18 or (h == 18 and m > 35):
            print_log(f"Seans kapandı ({now.strftime('%H:%M:%S')}). Görev tamamlandı.")
            break

        # 09:40 TR öncesinde bekle
        if h < 9 or (h == 9 and m < 40):
            print_log("Seans öncesi (09:40 TR öncesi). 60 saniye bekleniyor...")
            time.sleep(60)
            continue

        print_log(f"[DÖNGÜ {loop}/{max_loops}] Piyasa senkronizasyonu başlatılıyor...")
        run_sync_cycle()

        # 3 dakika bekle
        time.sleep(180)

if __name__ == "__main__":
    main()
