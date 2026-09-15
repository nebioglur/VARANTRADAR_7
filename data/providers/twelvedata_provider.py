import pandas as pd
import requests
import time
from datetime import datetime
from typing import Optional
from data.providers.base_provider import BaseDataProvider
from data.security import Vault

class TwelveDataProvider(BaseDataProvider):
    """
    CFG-03.1 — TERTIARY DATA PROVIDER (bağımsız 3. kanal)
    Twelve Data (twelvedata.com) üzerinden piyasa verisi çeker.
    Priority: 4 (Backup) — YFinance çökerse devreye giren bağımsız kaynak.

    - BIST destekler: sembol "THYAO" + exchange "XIST"
    - Gün içi (5min/1h) VE günlük bar destekler (Yahoo'nun tek rakibi burada)
    - Ücretsiz plan: 8 istek/dakika, 800 istek/gün → basit kota koruması var
    - API key gerekir: TWELVEDATA_API_KEY env değişkeni veya Vault ("TWELVEDATA")
    - Key yoksa boş DataFrame döner (failover zinciri zarar görmez)
    """

    BASE_URL = "https://api.twelvedata.com/time_series"

    # Ücretsiz plan kota koruması: dakikada en fazla 7 istek
    MAX_REQ_PER_MIN = 7

    def __init__(self):
        super().__init__()
        # ONCELIK: TWELVEDATA_API_KEY env degiskeni > kod icindeki yedek key
        self.api_key = Vault.get_key("TWELVEDATA") or "effa0f8851a74ac68a145b3ab422b273"
        self._minute_window_start = 0.0
        self._minute_req_count = 0

    def get_provider_name(self) -> str:
        return "TwelveData API"

    def get_priority(self) -> int:
        return 4  # Backup

    def _quota_allow(self) -> bool:
        """Dakikalik kota kontrolu (free plan: 8/dk)."""
        now = time.time()
        if now - self._minute_window_start >= 60:
            self._minute_window_start = now
            self._minute_req_count = 0
        if self._minute_req_count >= self.MAX_REQ_PER_MIN:
            return False
        self._minute_req_count += 1
        return True

    @staticmethod
    def _map_interval(interval: str) -> Optional[str]:
        mapping = {
            "1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
            "1h": "1h", "1d": "1day", "1day": "1day", "D": "1day",
            "1wk": "1week", "1mo": "1month",
        }
        return mapping.get(interval)

    def fetch_ohlcv(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        if not self.api_key:
            self._record_error()
            return pd.DataFrame()
        if not self._quota_allow():
            self._record_error()
            return pd.DataFrame()

        td_interval = self._map_interval(interval)
        if not td_interval:
            self._record_error()
            return pd.DataFrame()

        raw = str(symbol).upper()
        is_bist = raw.endswith('.IS')
        clean_symbol = raw.replace('.IS', '')
        params = {
            "symbol": clean_symbol,
            "interval": td_interval,
            "apikey": self.api_key,
            "order": "ASC",
        }
        if is_bist:
            params["exchange"] = "BIST"

        # Period -> bar sayisi tahmini
        days = {"1d": 2, "5d": 7, "1mo": 32, "3mo": 95, "6mo": 185, "1y": 370}.get(period, 32)
        if td_interval == "1day":
            params["outputsize"] = days
        elif td_interval in ("1h",):
            params["outputsize"] = min(days * 11, 5000)   # BIST seansi ~5.5 saat
        elif td_interval == "5min":
            params["outputsize"] = min(days * 70, 5000)
        else:
            params["outputsize"] = min(days * 40, 5000)

        try:
            start_time = time.time()
            resp = requests.get(self.BASE_URL, params=params, timeout=15)
            latency = (time.time() - start_time) * 1000

            if resp.status_code != 200:
                self._record_error()
                return pd.DataFrame()

            data = resp.json()
            if data.get("status") != "ok" or "values" not in data:
                self._record_error()
                return pd.DataFrame()

            records = []
            for v in data["values"]:
                try:
                    records.append({
                        "Date": pd.to_datetime(v.get("datetime")),
                        "Open": float(v.get("open")),
                        "High": float(v.get("high")),
                        "Low": float(v.get("low")),
                        "Close": float(v.get("close")),
                        "Volume": float(v.get("volume") or 0),
                    })
                except (ValueError, TypeError):
                    continue

            if not records:
                self._record_error()
                return pd.DataFrame()

            df = pd.DataFrame(records).sort_values("Date").set_index("Date")
            self._record_success(latency)
            return df

        except Exception:
            self._record_error()
            return pd.DataFrame()
