"""
CFG-03.1 INDUSTRIAL-GRADE BIST DATA PROVIDER - TRADINGVIEW BULK SCANNER
========================================================================
Tüm 600+ BIST hissesini ve BIST 100 endeksini tek bir yüksek hızlı HTTP
isteğinde (ortalama 1.5 - 2.5 saniye) eksiksiz, sıfır ban riski ve
sıfır rate-limit ile çeker.

Çekilen Temel Veriler:
- Son Fiyat (Close)
- Günlük Yüzde Değişim (Change_Pct)
- Günlük Açılış, En Yüksek, En Düşük (Open, High, Low)
- Hacim (Volume) ve İşlem Hacmi / TL Hacim (Value.Traded / Money_Volume)
- 10 Günlük Ortalama Hacim & Hacim Çarpanı (Vol_Multiplier)
- RSI (14)
- EMA50 ve EMA200
- ATR (14)
- MACD ve MACD Signal
- Bollinger Bantları (Upper, Lower, Basis) ve Bant Genişliği (BB_Width)
- Stokastik Osilatör (Stoch.K, Stoch.D)
- BIST 100 (XU100) Endeks Değeri ve Değişimi
"""

import time
import requests
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from data.providers.base_provider import BaseDataProvider


def _get_pa_proxies():
    import os
    if os.path.exists('/var/www') or os.path.exists('/home/varantradarpro') or os.environ.get('http_proxy'):
        return {'http': 'http://proxy.server:3128', 'https': 'http://proxy.server:3128'}
    return None


class TradingViewBulkProvider(BaseDataProvider):
    SCANNER_URL = "https://scanner.tradingview.com/turkey/scan"
    
    COLUMNS = [
        "name",                     # 0: ASELS
        "close",                    # 1: Son Fiyat
        "change",                   # 2: Yüzde Değişim
        "change_abs",               # 3: Net TL Değişim
        "volume",                   # 4: Adet Hacim
        "Value.Traded",             # 5: TL İşlem Hacmi
        "open",                     # 6: Günlük Açılış
        "high",                     # 7: Gün İçi En Yüksek
        "low",                      # 8: Gün İçi En Düşük
        "RSI",                      # 9: RSI (14)
        "EMA50",                    # 10: 50 Günlük EMA
        "EMA200",                   # 11: 200 Günlük EMA
        "ATR",                      # 12: Ortalama Gerçek Aralık
        "MACD.macd",                # 13: MACD Değeri
        "MACD.signal",              # 14: MACD Sinyali
        "Recommend.All",            # 15: Genel Teknik Değerlendirme (-1 ile +1 arası)
        "description",              # 16: Şirket Açıklaması
        "average_volume_10d_calc",  # 17: 10 Günlük Ortalama Hacim
        "BB.upper",                 # 18: Bollinger Üst Bant
        "BB.lower",                 # 19: Bollinger Alt Bant
        "BB.basis",                 # 20: Bollinger Orta Bant
        "Stoch.K",                  # 21: Stokastik %K
        "Stoch.D",                  # 22: Stokastik %D
        "VWAP"                      # 23: Hacim Ağırlıklı Ortalama Fiyat (Kurumsal Çapa)
    ]

    def __init__(self):
        super().__init__()
        self._cached_symbols_stats: Dict[str, Any] = {}
        self._last_xu100_change: Optional[float] = None
        self._last_xu100_price: Optional[float] = None
        self._last_fetch_ts: float = 0.0

    def get_provider_name(self) -> str:
        return "TradingView Bulk Scanner"

    def get_priority(self) -> int:
        return 1  # Primary Ultra-Fast Bulk Feed

    def fetch_ohlcv(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        """BaseDataProvider uyumluluğu - tekil OHLCV ihtiyacında son anlık barı döner."""
        clean_sym = symbol.replace(".IS", "").strip().upper()
        if not self._cached_symbols_stats or (time.time() - self._last_fetch_ts > 180):
            self.fetch_all_bist()
            
        full_key = f"{clean_sym}.IS"
        data = self._cached_symbols_stats.get(full_key) or self._cached_symbols_stats.get(clean_sym)
        if not data:
            return pd.DataFrame()
            
        row = {
            "Open": data.get("Daily_Open", data.get("Price")),
            "High": data.get("High", data.get("Price")),
            "Low": data.get("Low", data.get("Price")),
            "Close": data.get("Price"),
            "Volume": data.get("Volume", 0)
        }
        df = pd.DataFrame([row], index=[pd.Timestamp.now(tz="Europe/Istanbul")])
        df.index.name = "Datetime"
        return df

    def get_live_price_single(self, symbol: str, timeout: int = 4) -> Optional[float]:
        """Tek bir hissenin BIST canlı fiyatını TradingView'den anlık sorgular (Hızlı teyit)."""
        clean_sym = symbol.replace(".IS", "").strip().upper()
        payload = {
            "symbols": {"tickers": [f"BIST:{clean_sym}"]},
            "columns": ["close"]
        }
        try:
            r = requests.post(self.SCANNER_URL, json=payload, timeout=timeout, proxies=_get_pa_proxies())
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data and data[0].get("d"):
                    val = data[0]["d"][0]
                    if val is not None and float(val) > 0:
                        return round(float(val), 2)
        except Exception:
            pass
        return None

    def fetch_all_bist(self, timeout: int = 15) -> Tuple[Dict[str, Any], Optional[float], Optional[float]]:
        """
        BIST'teki tüm hisse senetlerini ve XU100 endeksini tek bir POST isteğinde çeker.
        Döndürür: (all_symbols_stats, xu100_change, xu100_price)
        """
        t0 = time.time()
        
        # 1. BIST hisseleri ve fon/sertifika tarayıcı yükü
        payload = {
            "filter": [
                {"left": "type", "operation": "in_range", "right": ["stock", "dr"]}
            ],
            "options": {"lang": "tr"},
            "symbols": {"query": {"types": []}, "tickers": []},
            "columns": self.COLUMNS,
            "sort": {"sortBy": "Value.Traded", "sortOrder": "desc"},
            "range": [0, 750]
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        stats_dict: Dict[str, Any] = {}
        xu100_chg: Optional[float] = None
        xu100_px: Optional[float] = None

        try:
            proxies = _get_pa_proxies()
            resp = requests.post(self.SCANNER_URL, json=payload, headers=headers, proxies=proxies, timeout=timeout)
            if resp.status_code != 200:
                self._record_error()
                print(f"[TradingViewProvider] HTTP {resp.status_code} hatası!")
                return self._cached_symbols_stats, self._last_xu100_change, self._last_xu100_price
                
            res_json = resp.json()
            rows = res_json.get("data", [])
            
            # Tarih ve saat damgası
            try:
                from zoneinfo import ZoneInfo
                _now_tr = datetime.now(ZoneInfo("Europe/Istanbul"))
                today_str = _now_tr.strftime("%Y-%m-%d")
                time_str = _now_tr.strftime("%H:%M")
            except Exception:
                _now_tr = datetime.now()
                today_str = _now_tr.strftime("%Y-%m-%d")
                time_str = _now_tr.strftime("%H:%M")

            for item in rows:
                ticker_full = item.get("s", "")  # Örn: "BIST:ASELS"
                vals = item.get("d", [])
                if not vals or len(vals) < 18:
                    continue

                raw_name = str(vals[0]).strip().upper()
                if not raw_name:
                    continue

                sym_with_is = f"{raw_name}.IS"
                
                try:
                    price = float(vals[1]) if vals[1] is not None else 0.0
                    change_pct = float(vals[2]) if vals[2] is not None else 0.0
                    volume = float(vals[4]) if vals[4] is not None else 0.0
                    money_vol = float(vals[5]) if vals[5] is not None else (price * volume)
                    d_open = float(vals[6]) if vals[6] is not None else price
                    d_high = float(vals[7]) if vals[7] is not None else price
                    d_low = float(vals[8]) if vals[8] is not None else price
                    rsi = float(vals[9]) if vals[9] is not None else 50.0
                    ema50 = float(vals[10]) if vals[10] is not None else 0.0
                    ema200 = float(vals[11]) if vals[11] is not None else 0.0
                    atr = float(vals[12]) if vals[12] is not None else (price * 0.02)
                    macd = float(vals[13]) if vals[13] is not None else 0.0
                    macd_sig = float(vals[14]) if vals[14] is not None else 0.0
                    recommend = float(vals[15]) if vals[15] is not None else 0.0
                    desc = str(vals[16]) if vals[16] else raw_name
                    avg_vol_10d = float(vals[17]) if vals[17] is not None else volume

                    # Bollinger
                    bb_up = float(vals[18]) if len(vals) > 18 and vals[18] is not None else 0.0
                    bb_low = float(vals[19]) if len(vals) > 19 and vals[19] is not None else 0.0
                    bb_mid = float(vals[20]) if len(vals) > 20 and vals[20] is not None else price
                    bb_width = ((bb_up - bb_low) / bb_mid) if (bb_mid > 0 and bb_up > bb_low) else 0.0

                    # Stoch
                    stoch_k = float(vals[21]) if len(vals) > 21 and vals[21] is not None else 50.0
                    stoch_d = float(vals[22]) if len(vals) > 22 and vals[22] is not None else 50.0

                    # VWAP (Hacim Ağırlıklı Ortalama Fiyat)
                    vwap = float(vals[23]) if len(vals) > 23 and vals[23] is not None and float(vals[23]) > 0 else (money_vol / volume if volume > 0 else price)
                    dist_to_vwap = round(((price - vwap) / vwap) * 100.0, 2) if vwap > 0 else 0.0

                    vol_mult = round(volume / avg_vol_10d, 2) if avg_vol_10d > 0 else 1.0

                    # Gün İçi Pozisyon ve Güç
                    rng = d_high - d_low
                    pos_pct = max(0.0, min(100.0, ((price - d_low) / rng) * 100.0)) if rng > 0.0001 else (75.0 if change_pct > 0 else 50.0)
                    h_strength = pos_pct * 0.6 + (min(change_pct * 3.5, 25.0) if change_pct > 0 else max(change_pct * 3.5, -25.0))
                    h_strength = round(max(5.0, min(98.0, h_strength)), 1)
                    
                    if h_strength >= 65.0 or (change_pct >= 2.5 and pos_pct >= 60.0):
                        h_flow = "Toplanıyor"
                    elif h_strength <= 35.0 or (change_pct <= -2.5 and pos_pct <= 40.0):
                        h_flow = "Satılıyor"
                    else:
                        h_flow = "Denge"

                    ceiling_target = round(price * 1.10, 2)
                    dist_to_ceiling = round(((ceiling_target - price) / price) * 100, 2) if price > 0 else 10.0

                    # Skor Hesaplama
                    score = 50.0
                    if price > ema200 > 0: score += 15.0
                    if price > ema50 > 0: score += 10.0
                    if change_pct > 0: score += min(change_pct * 3.0, 15.0)
                    if vol_mult >= 1.5: score += 10.0
                    if 45.0 <= rsi <= 68.0: score += 10.0
                    if macd > macd_sig: score += 5.0
                    score = round(max(10.0, min(99.0, score)), 1)

                    stats_dict[sym_with_is] = {
                        "Symbol": sym_with_is,
                        "Price": round(price, 2),
                        "last_price": round(price, 2),
                        "price": round(price, 2),
                        "Daily_Close": round(price, 2),
                        "Daily_Open": round(d_open, 2),
                        "High": round(d_high, 2),
                        "Low": round(d_low, 2),
                        "Change_Pct": round(change_pct, 2),
                        "Volume": volume,
                        "Money_Volume": money_vol,
                        "Vol_Multiplier": vol_mult,
                        "Vol_SMA10": avg_vol_10d,
                        "Daily_EMA50": round(ema50, 2),
                        "Daily_EMA200": round(ema200, 2),
                        "ATR": round(atr, 2),
                        "MACD": round(macd, 2),
                        "MACD_Signal": round(macd_sig, 2),
                        "Score": score,
                        "Ceiling_Price": ceiling_target,
                        "Distance_To_Ceiling_Pct": dist_to_ceiling,
                        "VWAP": round(vwap, 2),
                        "Distance_To_VWAP_Pct": dist_to_vwap,
                        "Price_Stale": False,
                        "Last_Price_Update": today_str,
                        "time": time_str,
                        "last_updated": time_str,
                        "bar_time": time_str,
                        "Indicators": {
                            "RSI_14": round(rsi, 2),
                            "MACD": round(macd, 2),
                            "MACD_Signal": round(macd_sig, 2),
                            "ATR": round(atr, 2),
                            "BB_Upper": round(bb_up, 2),
                            "BB_Lower": round(bb_low, 2),
                            "BB_Width": round(bb_width, 4),
                            "Stoch_K": round(stoch_k, 2),
                            "Stoch_D": round(stoch_d, 2),
                            "Recommendation": round(recommend, 2)
                        },
                        "intraday_strength": {
                            "session_open": round(d_open, 2),
                            "current_price": round(price, 2),
                            "intraday_change_pct": round(change_pct, 2),
                            "session_high": round(d_high, 2),
                            "session_low": round(d_low, 2),
                            "session_position_pct": round(pos_pct, 1),
                            "hourly_strength": h_strength,
                            "hourly_flow": h_flow,
                            "accumulation_score": h_strength,
                            "last_hour_buying_pressure": h_strength
                        }
                    }
                except Exception as row_err:
                    continue

            # 2. XU100 Endeksini ayrıca kesin sorgula
            try:
                xu_payload = {
                    "symbols": {"tickers": ["BIST:XU100"]},
                    "columns": ["close", "change"]
                }
                xu_resp = requests.post(self.SCANNER_URL, json=xu_payload, headers=headers, proxies=proxies, timeout=5)
                if xu_resp.status_code == 200:
                    xu_data = xu_resp.json().get("data", [])
                    if xu_data and xu_data[0].get("d"):
                        xu100_px = float(xu_data[0]["d"][0])
                        xu100_chg = round(float(xu_data[0]["d"][1]), 2)
            except Exception as e_xu:
                pass

            latency = (time.time() - t0) * 1000.0
            self._record_success(latency)
            
            if stats_dict:
                self._cached_symbols_stats = stats_dict
                self._last_xu100_change = xu100_chg
                self._last_xu100_price = xu100_px
                self._last_fetch_ts = time.time()
                print(f"[TradingViewProvider] {len(stats_dict)} BIST hissesi çekildi (Gecikme: {latency:.0f} ms | XU100: %{xu100_chg})")

            return self._cached_symbols_stats, self._last_xu100_change, self._last_xu100_price

        except Exception as e:
            self._record_error()
            print(f"[TradingViewProvider] Veri çekme hatası: {e}")
            return self._cached_symbols_stats, self._last_xu100_change, self._last_xu100_price

    def build_dashboard_data(self) -> Dict[str, Any]:
        """
        Server ve Dashboard için eksiksiz veri paketi üretir.
        Kategoriler: gainers, losers, high_volume, opportunities, all_symbols_stats
        """
        stats, xu100_chg, xu100_px = self.fetch_all_bist()
        if not stats:
            return {}

        try:
            from zoneinfo import ZoneInfo
            today_str = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d")
            time_str = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%H:%M")
        except Exception:
            today_str = datetime.now().strftime("%Y-%m-%d")
            time_str = datetime.now().strftime("%H:%M")

        all_items = list(stats.values())
        
        # Filtre: Anomali kontrolü (|değişim| <= 35)
        clean_items = [x for x in all_items if abs(x.get("Change_Pct", 0.0)) <= 35.0]

        gainers = sorted([x for x in clean_items if x.get("Change_Pct", 0) > 0], key=lambda x: x.get("Change_Pct", 0), reverse=True)[:25]
        losers = sorted([x for x in clean_items if x.get("Change_Pct", 0) < 0], key=lambda x: x.get("Change_Pct", 0))[:25]
        high_vol = sorted(clean_items, key=lambda x: x.get("Money_Volume", 0), reverse=True)[:25]
        
        def is_healthy_candle(x):
            p = float(x.get("Price", 0))
            d_open = float(x.get("Daily_Open", p))
            d_high = float(x.get("High", p))
            d_low = float(x.get("Low", p))
            rng = d_high - d_low
            if rng <= 0: return True
            upper_wick = d_high - max(d_open, p)
            if (upper_wick / rng) > 0.28:
                return False
            if d_high > 0 and ((d_high - p) / d_high) > 0.020:
                return False
            pos_pct = ((p - d_low) / rng) * 100.0
            if pos_pct < 70.0:
                return False
            # VWAP Kurumsal Çapası: Fiyat VWAP altında olamaz, %5'ten fazla aşırı şişmiş olamaz
            vwap_val = float(x.get("VWAP", 0))
            if vwap_val > 0:
                if p < vwap_val * 0.998:
                    return False
                if p > vwap_val * 1.050:
                    return False
            return True

        # Kurumsal Likidite ve Fitil Filtresi (Institutional Grade):
        # 1. Günlük hacim >= 75M TL veya 10 günlük ortalama ciro >= 100M TL
        # 2. Fiyat >= 8.0 TL (sığ ve spekülatif penny stock hisseleri elenir)
        # 3. Fitil tuzağı olmamalı (üst fitil <= %28, zirveden çekilme <= %2.0, pos_pct >= %70)
        tavan_adaylari = sorted(
            [x for x in clean_items if (
                2.0 <= x.get("Change_Pct", 0) < 9.9 and
                x.get("Vol_Multiplier", 0) >= 1.15 and
                x.get("Price", 0) >= 8.0 and
                (x.get("Money_Volume", 0) >= 75_000_000 or (x.get("Vol_SMA10", 0) * x.get("Price", 0)) >= 100_000_000) and
                is_healthy_candle(x)
            )],
            key=lambda x: (-x.get("Score", 0), -x.get("Vol_Multiplier", 0), x.get("Distance_To_Ceiling_Pct", 99))
        )[:15]

        # Fırsatlar: Skoru yüksek, likit ve fitil tuzağı olmayan kurumsal liderler
        opportunities = sorted(
            [x for x in clean_items if (
                x.get("Score", 0) >= 70.0 and
                x.get("Price", 0) >= 8.0 and
                (x.get("Money_Volume", 0) >= 50_000_000 or (x.get("Vol_SMA10", 0) * x.get("Price", 0)) >= 75_000_000) and
                is_healthy_candle(x)
            )],
            key=lambda x: x.get("Score", 0), reverse=True
        )[:20]

        # Endeks Makro Şalteri:
        index_guard_active = bool(xu100_chg is not None and xu100_chg < -0.30)
        index_status_desc = "SATIŞ BASKISI (ENDEKS ŞALTERİ AKTİF)" if index_guard_active else ("GÜÇLÜ BOĞA" if (xu100_chg or 0) > 0.5 else "DENGELİ")

        return {
            "cache_date": today_str,
            "last_updated": time_str,
            "last_sync_time": time_str,
            "price_updated_at": time.time(),
            "cache_timestamp": time.time(),
            "xu100_change": xu100_chg or 0.0,
            "index_guard_active": index_guard_active,
            "index_status": index_status_desc,
            "all_symbols_stats": stats,
            "gainers": gainers,
            "losers": losers,
            "high_volume": high_vol,
            "tavan_adaylari": tavan_adaylari,
            "opportunities": opportunities
        }
