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
                    xu100_change = float(cached_regime.get('xu100_trend') or 0.0)
            except Exception:
                all_stats = all_stats or {}
                xu100_change = xu100_change or 0.0

        if all_stats is None:
            all_stats = {}
        if xu100_change is None:
            xu100_change = 0.0

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
                ch = float(data.get("Change_Pct") or data.get("intraday_change_pct") or 0.0)
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
            pressure_pct = 50.0
            advance_pct = 50.0
            breadth_ratio = 1.0

        # Sektörel Ayrışma (Sector Relative Strength vs XU100)
        sector_divergence = {}
        for sec, ch_list in sector_stats.items():
            if ch_list:
                sec_avg = round(sum(ch_list) / len(ch_list), 2)
                rel_str = round(sec_avg - xu100_change, 2)
                sector_divergence[sec] = {
                    "avg_change": sec_avg,
                    "relative_strength": rel_str,
                    "is_divergent": rel_str >= 1.0,  # Endeksten en az +%1.0 pozitif ayrışan
                    "member_count": len(ch_list)
                }

        # KOMBİNE BASKI & REJİM HESAPLAMASI
        # XU100 eksi olsa dahi düşen hisse oranı %70'in üzerindeyse piyasa ağır satış baskısındadır.
        is_heavy_pressure = (pressure_pct >= 65.0) or (xu100_change < -0.8)
        is_extreme_crash = (pressure_pct >= 75.0) or (xu100_change < -1.5)

        if is_extreme_crash:
            regime_code = "STRONG_BEAR"
            regime_label = "ŞİDDETLİ ÇÖKÜŞ / AĞIR BASKI"
            regime_rule = f"Piyasanın %{pressure_pct}'i düşüşte! Yalnızca pozitif ayrışan süper A+ hisse (Max 1) veya %100 Nakit."
            max_positions = 0
        elif is_heavy_pressure or xu100_change < -0.4:
            regime_code = "BEAR"
            regime_label = "AYI BASKISI"
            regime_rule = f"Satış baskısı %{pressure_pct}. Yalnızca endekse meydan okuyan pozitif ayrışan sektörler serbest (Max 1)."
            max_positions = 1
        elif xu100_change > 0.5 and pressure_pct < 40.0:
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
            "xu100_change": round(xu100_change, 2),
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
            "sector_divergence": sector_divergence
        }

        cls._CACHE["timestamp"] = now
        cls._CACHE["data"] = result
        return result
