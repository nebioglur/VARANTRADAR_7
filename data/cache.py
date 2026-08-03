import os
import json
import time
import hashlib
from typing import Optional
import pandas as pd

class DataCache:
    """
    CFG-03.1 — CACHE ENGINE
    Üç katmanlı önbellekleme sistemi:
    
    1. RAM Cache: In-memory dict, 5 dakika TTL
    2. Disk Cache: JSON dosyaları, 24 saat TTL
    3. Historical Cache: Kalıcı (TTL yok), son çare yedek
    
    Amaç: API çağrılarını minimize etmek ve failover'da cache'ten beslenmek.
    """
    
    RAM_TTL_SECONDS = 300       # 5 dakika
    DISK_TTL_SECONDS = 86400    # 24 saat
    
    def __init__(self, cache_dir: str = None):
        self._ram_cache = {}  # key -> {"data": df, "timestamp": float}
        
        if cache_dir is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir = os.path.join(base, ".cache")
        
        self.cache_dir = cache_dir
        self.disk_dir = os.path.join(cache_dir, "disk")
        self.hist_dir = os.path.join(cache_dir, "historical")
        
        os.makedirs(self.disk_dir, exist_ok=True)
        os.makedirs(self.hist_dir, exist_ok=True)
    
    def _make_key(self, symbol: str, period: str, interval: str) -> str:
        raw = f"{symbol}_{period}_{interval}"
        return hashlib.md5(raw.encode()).hexdigest()
    
    # ==================== RAM CACHE ====================
    def get_ram(self, symbol: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        key = self._make_key(symbol, period, interval)
        entry = self._ram_cache.get(key)
        if entry and (time.time() - entry["timestamp"]) < self.RAM_TTL_SECONDS:
            return entry["data"]
        return None
    
    def set_ram(self, symbol: str, period: str, interval: str, df: pd.DataFrame):
        key = self._make_key(symbol, period, interval)
        self._ram_cache[key] = {"data": df.copy(), "timestamp": time.time()}
    
    # ==================== DISK CACHE ====================
    def get_disk(self, symbol: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        key = self._make_key(symbol, period, interval)
        path = os.path.join(self.disk_dir, f"{key}.json")
        
        if not os.path.exists(path):
            return None
        
        try:
            mtime = os.path.getmtime(path)
            if (time.time() - mtime) > self.DISK_TTL_SECONDS:
                return None  # Süresi dolmuş
            
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return pd.DataFrame(data)
        except:
            return None
    
    def set_disk(self, symbol: str, period: str, interval: str, df: pd.DataFrame):
        key = self._make_key(symbol, period, interval)
        path = os.path.join(self.disk_dir, f"{key}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(df.to_dict(orient="list"), f)
        except:
            pass
    
    # ==================== HISTORICAL CACHE ====================
    def get_historical(self, symbol: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        key = self._make_key(symbol, period, interval)
        path = os.path.join(self.hist_dir, f"{key}.json")
        
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return pd.DataFrame(data)
        except:
            return None
    
    def set_historical(self, symbol: str, period: str, interval: str, df: pd.DataFrame):
        """Historical cache'e kalıcı olarak yazar (TTL yok)."""
        key = self._make_key(symbol, period, interval)
        path = os.path.join(self.hist_dir, f"{key}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(df.to_dict(orient="list"), f)
        except:
            pass
    
    # ==================== UNIFIED GET ====================
    def get(self, symbol: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        """Önce RAM, sonra Disk, sonra Historical cache'e bakar."""
        result = self.get_ram(symbol, period, interval)
        if result is not None:
            return result
        
        result = self.get_disk(symbol, period, interval)
        if result is not None:
            self.set_ram(symbol, period, interval, result)  # RAM'e de yaz
            return result
        
        result = self.get_historical(symbol, period, interval)
        if result is not None:
            return result
        
        return None
    
    def set_all(self, symbol: str, period: str, interval: str, df: pd.DataFrame):
        """Tüm cache katmanlarına yazar."""
        self.set_ram(symbol, period, interval, df)
        self.set_disk(symbol, period, interval, df)
        self.set_historical(symbol, period, interval, df)
