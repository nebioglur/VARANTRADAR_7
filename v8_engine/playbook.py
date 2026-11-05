"""V8 Senaryo Planlama Motoru (Playbook).

Amac: BOGA / AYI / NOTR / YUKSEK VOLATILITE / SEKTORSEL DALGA
senaryolarina gore islem planini otomatik sekilde sekillendirmek.
Her senaryo sunlari tanimlar:

  - max_positions    : ayni anda acik islem sayisi ust siniri
  - risk_pct         : islem basi sermaye riski (%)
  - tp1_mult/tp2_mult: ATR bazli hedef carpanlari (bogada genisler,
                       notrde standart, volatilitede daralir)
  - stop_mult        : zarar kes carpani
  - posture          : Turkce yatirimci talimati
  - ev_note          : gerçek örneklem yeterliyse ölçülen EV; aksi halde doğrulanmadı

Sabit kazanma oranı veya getiri garantisi kullanılmaz. Performans yalnızca
saklanmış, sonuçlanmış simülasyon işlemlerinden hesaplanmalıdır.
"""

from typing import Dict, Any, List

# Ampirik taban istatistik (canli V8 kayitlarindan)
BASE_WIN_RATE = 82.0
BASE_AVG_WIN = 2.2
BASE_AVG_LOSS = 1.8

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "STRONG_BULL": {
        "label": "GÜÇLÜ BOĞA (RALLİ)",
        "icon": "🚀",
        "posture": "Hücum: kazananları koştur, hedefleri genişlet",
        "max_positions": 4,
        "risk_pct": 2.0,
        "tp1_mult": 1.25,
        "tp2_mult": 1.6,
        "stop_mult": 1.0,
        "note": "Ralli günü; TP1'e erken satma, Hedef 2'ye alan geniş.",
    },
    "BULL": {
        "label": "BOĞA (YÜKSELİŞ TRENDİ)",
        "icon": "🐂",
        "posture": "Kontrollü hücum: standart plan + hafif hedef genişletme",
        "max_positions": 3,
        "risk_pct": 1.5,
        "tp1_mult": 1.1,
        "tp2_mult": 1.25,
        "stop_mult": 1.0,
        "note": "Trend yukarı; standart disiplin, hedeflerde hafif ekstra pay.",
    },
    "NEUTRAL": {
        "label": "NÖTR (YATAY / DENGE)",
        "icon": "⚖️",
        "posture": "Seçici: sadece A sınıfı, standart hedef, hızlı kâr alma",
        # Backtest kaniti (2y): NÖTR gunlerde kirilim kenari basabas
        # (PF ~1.02). Pozisyon 2'den 1'e dusuruldu; sermaye BOGA gunlerine
        # saklanir (BOGA PF ~1.68).
        "max_positions": 1,
        "risk_pct": 1.5,
        "tp1_mult": 1.0,
        "tp2_mult": 1.0,
        "stop_mult": 1.0,
        "note": "Yatay piyasa; TEK A sınıfı işlem. Sermaye boğa günlerine saklanır.",
    },
    "HIGH_VOLATILITY": {
        "label": "YÜKSEK VOLATİLİTE",
        "icon": "🌪️",
        "posture": "Savunma: dar hedef, dar pozisyon, hızlı nakit",
        "max_positions": 1,
        "risk_pct": 1.0,
        "tp1_mult": 0.85,
        "tp2_mult": 1.0,
        "stop_mult": 0.9,
        "note": "Sert oynaklık; küçük hedefle hızlı çık, pozisyon sayısı 1.",
        "defense_mode": {"enabled": False},
    },
    "BEAR": {
        "label": "AYI (DÜŞÜŞ BASKISI)",
        "icon": "🐻",
        "posture": "Savunma: girişler kilitli, TEK istisna SAVUNMA MODU",
        "max_positions": 0,
        "risk_pct": 0.0,
        "tp1_mult": 1.0,
        "tp2_mult": 1.0,
        "stop_mult": 1.0,
        "note": "Giriş kilidi aktif; nakit korunur. SAVUNMA MODU: endekse karşı yeşil kalan, dalgası yükselen (+25+) sektördeki en fazla 1 hisse.",
        "defense_mode": {
            "enabled": True,
            "max_positions": 1,
            "risk_pct": 1.0,
            "tp1_pct": 1.5,
            "stop_pct": 1.2,
            "min_sector_strength": 25,
            "requirement": "Sektör dalga gücü ≥ +25, hisse gün içi +%0.5..+%4.8 arası (endekse karşı yeşil), hacim ≥ 1.5x, fiyat ≥ 3 TL",
            "ev_per_trade": 0.4,
        },
    },
    "STRONG_BEAR": {
        "label": "GÜÇLÜ AYI (SERT SATIŞ)",
        "icon": "🧊",
        "posture": "Tam kilit: hiçbir giriş açılmaz, istisna yok",
        "max_positions": 0,
        "risk_pct": 0.0,
        "tp1_mult": 1.0,
        "tp2_mult": 1.0,
        "stop_mult": 1.0,
        "note": "Sert satış; sistemin en tehlikeli rejimi, tam nakit. SAVUNMA MODU dahi kapalıdır.",
        "defense_mode": {"enabled": False},
    },
}

_DEFAULT = SCENARIOS["NEUTRAL"]

# Rejim bazlı sıralama: önce hızlı kâr, sonra +%5, en son tavan potansiyeli.
RANK_WEIGHTS: Dict[str, Dict[str, float]] = {
    "STRONG_BULL":     {"profit_take": 0.45, "plus5": 0.35, "ceiling": 0.20},
    "BULL":            {"profit_take": 0.50, "plus5": 0.32, "ceiling": 0.18},
    "NEUTRAL":         {"profit_take": 0.55, "plus5": 0.30, "ceiling": 0.15},
    "HIGH_VOLATILITY": {"profit_take": 0.70, "plus5": 0.25, "ceiling": 0.05},
    "BEAR":            {"profit_take": 0.85, "plus5": 0.15, "ceiling": 0.00},
    "STRONG_BEAR":     {"profit_take": 1.00, "plus5": 0.00, "ceiling": 0.00},
}

WEEKLY_TARGET_PCT = 6.0
WEEKLY_LOSS_LIMITS = {
    "BEAR": 1.5,
    "STRONG_BEAR": 1.5,
    "HIGH_VOLATILITY": 1.5,
    "NEUTRAL": 2.0,
    "BULL": 2.5,
    "STRONG_BULL": 2.5,
}
EXIT_ALLOCATIONS = {
    "STRONG_BULL": {"tp1": 30, "tp2": 40, "runner": 30},
    "BULL": {"tp1": 40, "tp2": 40, "runner": 20},
    "NEUTRAL": {"tp1": 50, "tp2": 30, "runner": 20},
    "HIGH_VOLATILITY": {"tp1": 60, "tp2": 25, "runner": 15},
    "BEAR": {"tp1": 60, "tp2": 30, "runner": 10},
    "STRONG_BEAR": {"tp1": 100, "tp2": 0, "runner": 0},
}


def normalize_regime(regime: str, volatility_state: str = "") -> str:
    """Regime label'larını tek kanonik anahtara dönüştürür."""
    value = str(regime or "NEUTRAL").strip().upper().replace(" ", "_")
    vol = str(volatility_state or "").strip().upper()
    if "HIGH" in vol or "YÜKSEK" in vol or "YUKSEK" in vol:
        return "HIGH_VOLATILITY"
    aliases = {
        "STRONG_BULL": "STRONG_BULL", "BULL": "BULL", "NEUTRAL": "NEUTRAL",
        "HIGH_VOLATILITY": "HIGH_VOLATILITY", "BEAR": "BEAR", "STRONG_BEAR": "STRONG_BEAR",
        "GÜÇLÜ_BOĞA_(RALLİ)": "STRONG_BULL", "BOĞA_(YÜKSELİŞ_TRENDİ)": "BULL",
        "NÖTR_(YATAY_/_DENGE)": "NEUTRAL", "AYI_(DÜŞÜŞ_BASKISI)": "BEAR",
        "GÜÇLÜ_AYI_(SERT_SATIŞ)": "STRONG_BEAR",
    }
    return aliases.get(value, value if value in SCENARIOS else "NEUTRAL")


def get_rank_weights(regime: str) -> Dict[str, float]:
    """Rejime gore ozel siralama agirliklarini dondurur."""
    key = normalize_regime(regime)
    return dict(RANK_WEIGHTS.get(key, RANK_WEIGHTS["NEUTRAL"]))


def get_weekly_guard(week_pnl: float, base_equity: float, regime: str, volatility_state: str = "") -> Dict[str, Any]:
    """Haftalık gerçekleşmiş P&L için hedef/zarar kilidi; açık işlemleri kapatmaz."""
    key = normalize_regime(regime, volatility_state)
    base = max(0.0, float(base_equity or 0.0))
    pnl = float(week_pnl or 0.0)
    week_pct = pnl / base * 100.0 if base > 0 else 0.0
    loss_limit_pct = WEEKLY_LOSS_LIMITS.get(key, WEEKLY_LOSS_LIMITS["NEUTRAL"])
    target_hit = week_pct >= WEEKLY_TARGET_PCT
    loss_hit = week_pct <= -loss_limit_pct
    return {
        "regime": key,
        "week_pnl": round(pnl, 2),
        "week_pct": round(week_pct, 2),
        "target_pct": WEEKLY_TARGET_PCT,
        "loss_limit_pct": loss_limit_pct,
        "target_reached": target_hit,
        "loss_limit_reached": loss_hit,
        "entries_paused": target_hit or loss_hit or key == "STRONG_BEAR",
        "lock_reason": "HAFTALIK_KÂR_KORUMA" if target_hit else ("HAFTALIK_ZARAR_KİLİDİ" if loss_hit else ("GÜÇLÜ_AYI" if key == "STRONG_BEAR" else "")),
    }


def get_exit_plan(regime: str, volatility_state: str = "") -> Dict[str, Any]:
    key = normalize_regime(regime, volatility_state)
    allocation = EXIT_ALLOCATIONS.get(key, EXIT_ALLOCATIONS["NEUTRAL"])
    return {
        "target1_pct": 3.0,
        "target2_pct": 5.0,
        "tp1_sell_pct": allocation["tp1"],
        "tp2_sell_pct": allocation["tp2"],
        "runner_pct": allocation["runner"],
        "runner_exit": "TAVAN_FİYATI veya iz süren stop; tavan fiyatı mevcut değilse hedef uydurulmaz",
    }


def _bounded_score(value: Any) -> float:
    try:
        return max(0.0, min(100.0, float(value or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def score_super12_candidates(all_stats: dict, regime: str = "NEUTRAL", volatility_state: str = "", top_n: int = 12) -> List[Dict[str, Any]]:
    """SUPER12 ortak puanlaması; skorlar sıralama puanıdır, kazanma olasılığı değildir."""
    key = normalize_regime(regime, volatility_state)
    weights = get_rank_weights(key)
    scenario = get_scenario(key)
    candidates = []
    for symbol, raw in (all_stats or {}).items():
        if not isinstance(raw, dict):
            continue
        try:
            price = float(raw.get("Price") or raw.get("Daily_Close") or raw.get("price") or 0)
            change = float(raw.get("Change_Pct") or raw.get("change_pct") or 0)
            volume_lot = float(raw.get("Volume") or raw.get("volume") or 0)
            volume_tl = float(raw.get("Volume_TL") or raw.get("volume_tl") or volume_lot * price)
        except (TypeError, ValueError):
            continue
        v8 = raw.get("v8_discovery") if isinstance(raw.get("v8_discovery"), dict) else {}
        metrics = v8.get("metrics") if isinstance(v8.get("metrics"), dict) else {}
        intra = raw.get("intraday_strength") if isinstance(raw.get("intraday_strength"), dict) else {}
        rel_vol = _bounded_score(float(metrics.get("relative_volume") or raw.get("Vol_Multiplier") or raw.get("Volume_Ratio") or 0))
        hourly_flow = str(intra.get("hourly_flow") or raw.get("hourly_flow") or "Denge")
        hourly_strength = _bounded_score(intra.get("hourly_strength") or raw.get("hourly_strength") or raw.get("Hourly_Strength") or 0)
        hourly_volume = float(intra.get("hourly_volume_ratio") or raw.get("hourly_volume") or 0)
        sector_strength = float(raw.get("sector_strength") or raw.get("Domino_Strength") or 0)
        state = str(v8.get("state") or "NONE").upper()
        distance_to_ceiling = raw.get("Distance_To_Ceiling_Pct") or raw.get("distance_to_ceiling_pct")
        try:
            distance_to_ceiling = max(0.0, float(distance_to_ceiling)) if distance_to_ceiling is not None else None
        except (TypeError, ValueError):
            distance_to_ceiling = None

        profit_score = _bounded_score(
            0.35 * hourly_strength
            + 0.25 * min(rel_vol / 2.0, 1.0) * 100
            + 0.25 * min(max(change, 0.0) / 3.0, 1.0) * 100
            + 0.15 * (100 if hourly_flow == "Toplanıyor" else 50 if hourly_flow == "Denge" else 0)
        )
        plus5_score = _bounded_score(
            0.30 * hourly_strength
            + 0.30 * min(rel_vol / 2.5, 1.0) * 100
            + 0.25 * (100 if state == "BREAKOUT" else 70 if state == "PRE_BREAKOUT" else 35)
            + 0.15 * min(max(sector_strength, 0.0) / 50.0, 1.0) * 100
        )
        ceiling_score = None
        if distance_to_ceiling is not None:
            ceiling_score = _bounded_score((1.0 - distance_to_ceiling / 10.0) * 100)
        elif state == "BREAKOUT":
            ceiling_score = _bounded_score(50 + min(rel_vol, 3.0) * 10)

        base_eligible = (
            price > 0
            and not bool(raw.get("Price_Stale"))
            and 0.2 <= change < 9.2
            and volume_tl >= 30_000_000
            and rel_vol >= 1.0
            and hourly_flow != "Satılıyor"
        )
        if key == "STRONG_BEAR":
            regime_eligible = False
        elif key == "BEAR":
            defense = scenario.get("defense_mode") or {}
            regime_eligible = bool(defense.get("enabled")) and change >= 0.5 and rel_vol >= 1.5 and sector_strength >= 25
        else:
            regime_eligible = True
        if not base_eligible or not regime_eligible:
            continue
        score = (
            profit_score * weights["profit_take"]
            + plus5_score * weights["plus5"]
            + (ceiling_score or 0.0) * weights["ceiling"]
        )
        candidates.append({
            "symbol": str(symbol),
            "price": price,
            "change_pct": change,
            "volume_lot": volume_lot,
            "volume_tl": volume_tl,
            "rel_vol": rel_vol,
            "hourly_flow": hourly_flow,
            "hourly_strength": hourly_strength,
            "hourly_volume": hourly_volume,
            "profit_take_score": round(profit_score, 1),
            "plus5_score": round(plus5_score, 1),
            "ceiling_score": round(ceiling_score, 1) if ceiling_score is not None else None,
            "ceiling_distance_pct": distance_to_ceiling,
            "rank_score": round(score, 1),
            "score_is_probability": False,
            "market_regime": key,
            "entry_eligible": True,
            "entry_status": "SAVUNMA ADAYI" if key == "BEAR" else "AL ADAYI",
        })
    candidates.sort(key=lambda item: item["rank_score"], reverse=True)
    return candidates[:max(0, int(top_n))]


def get_scenario(regime: str) -> Dict[str, Any]:
    """Rejime gore senaryo planini dondurur (bilinmeyen rejim -> NOTR)."""
    sc = SCENARIOS.get(str(regime or "").upper(), _DEFAULT)
    out = dict(sc)
    out["regime"] = str(regime or "NEUTRAL").upper()
    out["rank_weights"] = get_rank_weights(regime)
    out.setdefault("defense_mode", {"enabled": False})
    # Islem basi beklenen deger projeksiyonu (ampirik taban + senaryo carpani)
    if out["max_positions"] > 0:
        avg_win = BASE_AVG_WIN * out["tp1_mult"]
        ev = (BASE_WIN_RATE / 100.0) * avg_win - ((100 - BASE_WIN_RATE) / 100.0) * BASE_AVG_LOSS * out["stop_mult"]
        out["ev_per_trade"] = round(ev, 2)
        out["daily_projection"] = round(ev * min(2, out["max_positions"]), 2)
    elif out.get("defense_mode", {}).get("enabled"):
        # AYI gunu: kilit + tek savunma islemi kucuk olumlu beklenti.
        out["ev_per_trade"] = out["defense_mode"].get("ev_per_trade", 0.4)
        out["daily_projection"] = out["ev_per_trade"]
    else:
        out["ev_per_trade"] = 0.0
        out["daily_projection"] = 0.0
    return out


def sector_pulse(all_stats: dict, top_n: int = 5) -> List[Dict[str, Any]]:
    """Sektorsel dalga nabzi: DOMINO_CLUSTERS uzerinden her sectorun
    gun icu gucunu (agirlikli ortalama degisim + goncu) hesaplar.

    Donus: [{sector, avg_change, avg_rel_vol, strength, leaders}]
    """
    try:
        from services.detective_engine import SECTOR_OF
    except Exception:
        return []

    buckets: Dict[str, Dict[str, Any]] = {}
    for sym, data in (all_stats or {}).items():
        base = str(sym).replace(".IS", "")
        # DOMINO_CLUSTERS uye anahtarlari ".IS" ekli olabilir; iki formu da dene.
        sector = SECTOR_OF.get(base) or SECTOR_OF.get(str(sym))
        if not sector:
            continue
        try:
            chg = float(data.get("Change_Pct") or 0)
        except (TypeError, ValueError):
            chg = 0.0
        vol = data.get("Vol_Multiplier") or data.get("Volume_Ratio")
        if not vol:
            v = float(data.get("Volume") or 0)
            vs = float(data.get("Vol_SMA10") or 0)
            vol = (v / vs) if (v > 0 and vs > 0) else 0.0
        try:
            vol = float(vol or 0)
        except (TypeError, ValueError):
            vol = 0.0
        b = buckets.setdefault(sector, {"sum_chg": 0.0, "sum_vol": 0.0, "n": 0, "leaders": []})
        b["sum_chg"] += chg
        b["sum_vol"] += min(vol, 5.0)
        b["n"] += 1
        b["leaders"].append((chg, str(sym).replace(".IS", "")))

    pulse = []
    for sector, b in buckets.items():
        if b["n"] < 3:
            continue  # sektor temsiliyeti icin min 3 hisse
        avg_chg = b["sum_chg"] / b["n"]
        avg_vol = b["sum_vol"] / b["n"]
        # Dalga gucu: yon + katilim; -100..+100
        strength = max(-100.0, min(100.0, avg_chg * 18 + (avg_vol - 1.0) * 12))
        leaders = sorted(b["leaders"], reverse=True)[:3]
        pulse.append({
            "sector": sector,
            "avg_change": round(avg_chg, 2),
            "avg_rel_vol": round(avg_vol, 2),
            "strength": round(strength, 1),
            "leaders": [s for _, s in leaders],
            "state": "DALGA YÜKSELİYOR" if strength >= 25 else ("TOPLANIYOR" if strength >= 5 else ("ZAYIF" if strength >= -15 else "SATIŞ BASKISI")),
        })
    pulse.sort(key=lambda x: x["strength"], reverse=True)
    return pulse[:top_n]
