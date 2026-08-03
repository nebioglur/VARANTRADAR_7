"""
VarantRadar Pro - Önbellekleme (Cache) Sistemi
"""
from cachetools import TTLCache, cached

# Veritabanı okumaları ve API çağrıları için 5 dakikalık (300 saniye) önbellek
data_cache = TTLCache(maxsize=1000, ttl=300)

def clear_cache():
    """Önbelleği temizler"""
    data_cache.clear()
