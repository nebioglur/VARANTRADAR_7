import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from typing import Optional
from data.providers.base_provider import BaseDataProvider

class IsYatirimProvider(BaseDataProvider):
    """
    BACKUP DATA PROVIDER — İş Yatırım açık veri servisi.
    Priority: 3 (Backup) — YFinance ve Finnhub çalışmazsa devreye girer.

    - Yalnızca BIST hisseleri (THYAO, ASELS... .IS eki opsiyonel)
    - Yalnızca GÜNLÜK bar (interval='1d'); gün içi isteklerde boş dönüp
      failover zincirinin devam etmesini sağlar
    - API key gerektirmez
    Not: Serviste Açılış kolonu yoktur; AOF (ağırlıklı ortalama fiyat) Open
    olarak kullanılır.
    """

    BASE_URL = "https://www.isyatirim.com.tr/_layouts/15/Isyatirim.Website/Common/Data.aspx/HisseTekil"

    def get_provider_name(self) -> str:
        return "IsYatirim API"

    def get_priority(self) -> int:
        return 3  # Backup

    def fetch_ohlcv(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        # Sadece günlük veri desteklenir
        if interval not in ("1d", "1day", "D"):
            self._record_error()
            return pd.DataFrame()

        clean_symbol = symbol.replace(".IS", "").strip().upper()
        if not clean_symbol or not clean_symbol.isalnum():
            self._record_error()
            return pd.DataFrame()

        period_days = {"1d": 5, "5d": 7, "1mo": 32, "3mo": 95,
                       "6mo": 185, "1y": 370, "2y": 740}.get(period, 32)

        try:
            start_time = time.time()
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=period_days)
            params = {
                "hisse": clean_symbol,
                "startdate": start_dt.strftime("%d-%m-%Y"),
                "enddate": end_dt.strftime("%d-%m-%Y"),
            }
            resp = requests.get(self.BASE_URL, params=params, timeout=15,
                                headers={"User-Agent": "Mozilla/5.0"})
            latency = (time.time() - start_time) * 1000

            if resp.status_code != 200:
                self._record_error()
                return pd.DataFrame()

            rows = (resp.json() or {}).get("value") or []
            if not rows:
                self._record_error()
                return pd.DataFrame()

            records = []
            for r in rows:
                try:
                    close = r.get("HGDG_KAPANIS")
                    if close is None:
                        continue
                    records.append({
                        "Date": datetime.strptime(r.get("HGDG_TARIH"), "%d-%m-%Y"),
                        "Open": float(r.get("HGDG_AOF") or close),
                        "High": float(r.get("HGDG_MAX") or close),
                        "Low": float(r.get("HGDG_MIN") or close),
                        "Close": float(close),
                        "Volume": float(r.get("HGDG_HACIM") or 0),
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
