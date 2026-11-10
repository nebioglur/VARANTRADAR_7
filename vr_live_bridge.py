"""
VARANTRADAR PRO - CANLI VERI & OTO-PING KOPRUSU
Verdent Cloud (Canli 609 BIST Verisi) -> PythonAnywhere (V8 & Simulasyon Motoru)

Kullanim:
  Tek seferlik calistirma: python vr_live_bridge.py --once
  Surekli arka plan:       python vr_live_bridge.py
"""

import sys
import time
import json
import os
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
import requests

VERDENT_URL = "https://varantradar-pro-8.verdent.app"
PA_URL = "https://varantradarpro.pythonanywhere.com"
AUTH_TOKEN = "pro8_sync"

def get_istanbul_time():
    if ZoneInfo:
        return datetime.now(ZoneInfo("Europe/Istanbul"))
    return datetime.now()

def sync_once():
    now = get_istanbul_time()
    t_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%Y-%m-%d")

    session = requests.Session()
    
    # 1. Verdent Login
    try:
        r_log = session.post(f"{VERDENT_URL}/login", json={"username": "nebioglur", "password": "123"}, timeout=12)
        if r_log.status_code != 200:
            print(f"[{t_str}] [HATA] Verdent oturum acilamadi (HTTP {r_log.status_code})")
            return False
    except Exception as e:
        print(f"[{t_str}] [HATA] Verdent erisim hatasi: {e}")
        return False

    # 2. Verdent Dashboard Data Cek
    try:
        r_dash = session.get(f"{VERDENT_URL}/api/dashboard_init", timeout=25)
        if r_dash.status_code != 200:
            print(f"[{t_str}] [HATA] Verdent dashboard_init alinamadi (HTTP {r_dash.status_code})")
            return False
        dash_json = r_dash.json()
        dash_data = dash_json.get("dashboard_data", {})
        xu100_change = dash_json.get("xu100_change")
        symbols_count = len(dash_data.get("all_symbols_stats", {}))
        if symbols_count == 0:
            print(f"[{t_str}] [UYARI] Verdent hisse listesi bos!")
            return False
    except Exception as e:
        print(f"[{t_str}] [HATA] Verdent veri indirme hatasi: {e}")
        return False

    # 3. Verdent V8 Breakout Cek (Opsiyonel)
    v8_bo_data = None
    try:
        r_v8 = session.get(f"{VERDENT_URL}/api/v8/radar/breakout", timeout=15)
        if r_v8.status_code == 200:
            v8_bo_data = r_v8.json()
    except Exception:
        pass

    # 4. PythonAnywhere'e Veri Enjekte Et (Push Market Data)
    payload = {
        "token": AUTH_TOKEN,
        "dashboard_data": dash_data,
        "v8_breakout_data": v8_bo_data,
        "xu100_change": xu100_change
    }

    try:
        r_push = requests.post(
            f"{PA_URL}/api/system/push_market_data?token={AUTH_TOKEN}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=35
        )
        if r_push.status_code == 200:
            res = r_push.json()
            regime = dash_data.get("v8_market_regime", {}).get("regime", "NEUTRAL")
            print(f"[{t_str}] [OK] {symbols_count} Hisse Senkronize Edildi | Rejim: {regime} | PA Simulasyon: {res.get('simulation', {}).get('status')}")
            return True
        else:
            print(f"[{t_str}] [HATA] PA push basarisiz (HTTP {r_push.status_code}): {r_push.text[:120]}")
            return False
    except Exception as e:
        print(f"[{t_str}] [HATA] PA baglanti hatasi: {e}")
        return False

def main():
    print("=" * 65)
    print("  VARANTRADAR PRO - CANLI VERI & OTO-PING KOPRUSU")
    print(f"  Kaynak: {VERDENT_URL}")
    print(f"  Hedef:  {PA_URL}")
    print("=" * 65)

    if "--once" in sys.argv:
        print("\n-> Tek seferlik senkronizasyon baslatiliyor...")
        ok = sync_once()
        sys.exit(0 if ok else 1)

    print("\n-> Surekli arka plan modu aktif (Piyasa saatlerinde her 8 dakikada bir).")
    print("   Durdurmak icin Ctrl+C tusuna basin.\n")

    while True:
        try:
            now = get_istanbul_time()
            weekday = now.weekday() < 5
            hour = now.hour
            minute = now.minute

            # Seans araligi: 09:50 - 18:15 (Pzt - Cuma)
            in_session = weekday and ((hour == 9 and minute >= 50) or (10 <= hour < 18) or (hour == 18 and minute <= 15))

            # Seans ve seans disi: 8 dakikada bir (480 saniye)
            interval = 480

            if in_session:
                print(f"[SEANS AKTIF] Veri senkronizasyonu yapiliyor ({now.strftime('%H:%M:%S')})...")
            else:
                print(f"[SEANS DISI / UYKU ONLEME] Ping gonderiliyor ({now.strftime('%H:%M:%S')})...")

            sync_once()

        except KeyboardInterrupt:
            print("\nKullanici tarafindan durduruldu.")
            break
        except Exception as e:
            print(f"[DONGU HATASI] {e}")

        time.sleep(interval)

if __name__ == "__main__":
    main()
