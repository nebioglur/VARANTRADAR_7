"""
Verdent'ten guncel piyasa verilerini cek ve lokal dosyalara kaydet.
Sonra git push + deploy ile PythonAnywhere'e aktar.
"""
import requests, json, os

BASE = 'https://varantradar-pro-8.verdent.app'
PROJECT = r'c:\Users\nebioglur\Desktop\TUM MASAUSTU_Kurtarilan\TUM MASAUSTU\VarantRadarPro'

s = requests.Session()

# 1. Login
print("1. Verdent login...")
r = s.post(f'{BASE}/login', json={'username': 'nebioglur', 'password': '123'}, timeout=15)
print(f"   Login: {r.status_code}")
if r.status_code != 200:
    print("   HATA: Login basarisiz!")
    exit(1)

# 2. Dashboard init (BIST verileri, rejim, trend, vs)
print("2. Dashboard verisi...")
r = s.get(f'{BASE}/api/dashboard_init', timeout=30)
print(f"   Dashboard: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    dash = data.get('dashboard_data', {})
    if dash and 'all_symbols_stats' in dash:
        # Rejim verisini kontrol et
        regime = dash.get('v8_market_regime', {})
        print(f"   Rejim: {regime.get('regime', '?')} | Guc: {regime.get('score', '?')} | XU100 Trend: {regime.get('xu100_trend', '?')}")
        print(f"   Sembol sayisi: {len(dash.get('all_symbols_stats', {}))}")
        print(f"   Cache tarihi: {dash.get('cache_date', '?')}")
        
        # Kaydet
        cache_path = os.path.join(PROJECT, 'dashboard_cache.json')
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(dash, f, ensure_ascii=False)
        print(f"   dashboard_cache.json kaydedildi ({os.path.getsize(cache_path) / 1024 / 1024:.1f} MB)")
    else:
        print("   HATA: Dashboard verisi bos!")

# 3. V8 Market Regime (ayrica)
print("3. V8 Market Regime...")
r = s.get(f'{BASE}/api/v8/market/regime', timeout=15)
print(f"   Regime endpoint: {r.status_code}")
if r.status_code == 200:
    regime_data = r.json()
    print(f"   Rejim: {regime_data.get('regime', '?')}")
    print(f"   Skor: {regime_data.get('score', '?')}")
    print(f"   XU100 Trend: {regime_data.get('xu100_trend', '?')}")

# 4. V8 Breakout (guncelle)
print("4. V8 Breakout...")
r = s.get(f'{BASE}/api/v8/radar/breakout', timeout=20)
print(f"   Breakout: {r.status_code}")
if r.status_code == 200:
    v8_data = r.json()
    items = v8_data.get('data', [])
    from collections import Counter
    counts = Counter(d.get('entry_status') for d in items)
    print(f"   Sayilar: {dict(counts)}")
    
    cache_path = os.path.join(PROJECT, 'v8_breakout_cache.json')
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(v8_data, f, ensure_ascii=False, indent=2)
    print(f"   v8_breakout_cache.json guncellendi")

# 5. V8 Weekly
print("5. V8 Weekly...")
r = s.get(f'{BASE}/api/v8/weekly', timeout=15)
print(f"   Weekly: {r.status_code}")
if r.status_code == 200:
    w = r.json()
    print(f"   Hafta PnL: {w.get('week_pnl')}, Pct: {w.get('week_pct')}, Trades: {w.get('trades_count')}")

print("\n=== TAMAMLANDI ===")
print("Simdi git add + commit + push + deploy yapilacak")
