import time
import math
import json
import logging

logger = logging.getLogger(__name__)

class MarketBreadthEngine:
    _CACHE = {
        "timestamp": 0.0,
        "data": None
    }
    CACHE_TTL = 30.0  # 30 saniye önbellek

    @classmethod
    def get_market_breadth(cls, all_stats: dict = None, xu100_change: float = None) -> dict:
        now = time.time()
        if all_stats is None and xu100_change is None and (now - cls._CACHE["timestamp"] < cls.CACHE_TTL) and cls._CACHE["data"]:
            return cls._CACHE["data"]

        cached_regime = None
        if all_stats is None or xu100_change is None:
            try:
                with open('dashboard_cache.json', encoding='utf-8') as f:
                    cached = json.load(f)
                if all_stats is None:
                    all_stats = cached.get('all_symbols_stats', {})
                if xu100_change is None:
                    cached_regime = cached.get('v8_market_regime', {})
                    cached_change = cached_regime.get('xu100_trend')
                    if cached_change is not None:
                        xu100_change = float(cached_change)
            except Exception:
                all_stats = all_stats or {}
                # Missing index data remains missing; do not manufacture a 0% move.

        if all_stats is None:
            all_stats = {}
        if xu100_change is not None:
            try:
                xu100_change = float(xu100_change)
                if not math.isfinite(xu100_change):
                    xu100_change = None
            except (TypeError, ValueError):
                xu100_change = None

        advances = 0
        declines = 0
        neutral = 0
        total = 0
        
        sector_stats = {}

        # Sektör kümeleme eşleştirmesi
        from config.bist_symbols import DOMINO_CLUSTERS
        sector_lookup = {}
        for sec_name, members in DOMINO_CLUSTERS.items():
            for m in members:
                sector_lookup[m] = sec_name
                sector_lookup[m.replace(".IS", "")] = sec_name

        for sym, data in all_stats.items():
            if not isinstance(data, dict):
                continue
            try:
                raw_change = data.get("Change_Pct")
                if raw_change is None:
                    raw_change = data.get("intraday_change_pct")
                if raw_change is None:
                    continue
                ch = float(raw_change)
                if not math.isfinite(ch):
                    continue
                total += 1
                if ch > 0.25:
                    advances += 1
                elif ch < -0.25:
                    declines += 1
                else:
                    neutral += 1

                # Sektörel getiri toplama
                clean_s = sym.replace(".IS", "")
                sec = sector_lookup.get(sym) or sector_lookup.get(clean_s)
                if sec:
                    if sec not in sector_stats:
                        sector_stats[sec] = []
                    sector_stats[sec].append(ch)
            except Exception:
                continue

        active = advances + declines
        if active > 0:
            pressure_pct = round((declines / active) * 100.0, 1)
            advance_pct = round((advances / active) * 100.0, 1)
            breadth_ratio = round(advances / declines, 2) if declines > 0 else 99.0
        else:
            pressure_pct = None
            advance_pct = None
            breadth_ratio = None

        # Sektörel Ayrışma (Sector Relative Strength vs XU100)
        sector_divergence = {}
        for sec, ch_list in sector_stats.items():
            if ch_list:
                sec_avg = round(sum(ch_list) / len(ch_list), 2)
                rel_str = round(sec_avg - xu100_change, 2) if xu100_change is not None else None
                sector_divergence[sec] = {
                    "avg_change": sec_avg,
                    "relative_strength": rel_str,
                    "is_divergent": rel_str is not None and rel_str >= 1.0,  # Endeksten en az +%1.0 pozitif ayrışan
                    "member_count": len(ch_list)
                }

        # KOMBİNE BASKI & REJİM HESAPLAMASI
        # XU100 eksi olsa dahi düşen hisse oranı %70'in üzerindeyse piyasa ağır satış baskısındadır.
        if total == 0 and xu100_change is None:
            result = {
                "data_status": "DATA_INSUFFICIENT",
                "xu100_change": None,
                "total_symbols": 0,
                "advances": 0,
                "declines": 0,
                "neutral": 0,
                "pressure_pct": None,
                "advance_pct": None,
                "breadth_ratio": None,
                "is_heavy_pressure": None,
                "is_extreme_crash": None,
                "regime_code": "DATA_INSUFFICIENT",
                "regime_label": "VERİ BEKLENİYOR",
                "regime_rule": "Endeks ve piyasa genişliği verisi bulunamadı; rejim üretilmedi.",
                "max_positions": 0,
                "sector_divergence": {},
                "breadth_available": False,
            }
            cls._CACHE["timestamp"] = now
            cls._CACHE["data"] = result
            return result

        is_heavy_pressure = (pressure_pct is not None and pressure_pct >= 65.0) or (xu100_change is not None and xu100_change < -0.8)
        is_extreme_crash = (pressure_pct is not None and pressure_pct >= 75.0) or (xu100_change is not None and xu100_change < -1.5)

        if is_extreme_crash:
            regime_code = "STRONG_BEAR"
            regime_label = "ŞİDDETLİ ÇÖKÜŞ / AĞIR BASKI"
            regime_rule = f"Piyasanın %{pressure_pct}'i düşüşte! Yalnızca pozitif ayrışan süper A+ hisse (Max 1) veya %100 Nakit."
            max_positions = 0
        elif (is_heavy_pressure and xu100_change < 0.0) or (xu100_change is not None and xu100_change < -0.6):
            regime_code = "BEAR"
            regime_label = "AYI BASKISI"
            regime_rule = f"Satış baskısı %{pressure_pct}. Yalnızca endekse meydan okuyan pozitif ayrışan sektörler serbest (Max 1)."
            max_positions = 1
        elif xu100_change is not None and xu100_change > 0.5 and (pressure_pct is None or pressure_pct < 40.0):
            regime_code = "BULL"
            regime_label = "GÜÇLÜ BOĞA RÜZGARI"
            regime_rule = f"Alıcı baskısı %{advance_pct}. Trend pozitif, 4 hisse tam kapasite hücum."
            max_positions = 4
        else:
            regime_code = "NEUTRAL"
            regime_label = "DENGELİ / NÖTR PİYASA"
            regime_rule = "Yön arayışı. Max 2 pozisyon, sıkı filtreli kırılımlar."
            max_positions = 2

        result = {
            "data_status": "OK" if total > 0 and xu100_change is not None else "PARTIAL",
            "xu100_change": round(xu100_change, 2) if xu100_change is not None else None,
            "total_symbols": total,
            "advances": advances,
            "declines": declines,
            "neutral": neutral,
            "pressure_pct": pressure_pct,
            "advance_pct": advance_pct,
            "breadth_ratio": breadth_ratio,
            "is_heavy_pressure": is_heavy_pressure,
            "is_extreme_crash": is_extreme_crash,
            "regime_code": regime_code,
            "regime_label": regime_label,
            "regime_rule": regime_rule,
            "max_positions": max_positions,
            "sector_divergence": sector_divergence,
            "breadth_available": total > 0,
        }

        cls._CACHE["timestamp"] = now
        cls._CACHE["data"] = result
        return result
