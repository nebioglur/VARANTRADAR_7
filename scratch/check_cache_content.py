import json

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

print('Keys in dashboard_cache:', list(cache.keys()))
tavan = cache.get('tavan_adaylari', [])
print('tavan_adaylari count:', len(tavan))
if tavan:
    print('Sample tavan candidate:', tavan[0])
regime = cache.get('v8_market_regime', {})
print('v8_market_regime:', regime)
