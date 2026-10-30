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
  - ev_note          : islem basi beklenen deger projeksiyonu

Beklenen deger (EV) hesabi ampirik canli istatistige dayanir:
kazanma ~%82, ort kazanc +2.2%, ort zarar -1.8% (TP1 + freeroll dahil).
Bu sabit bir garanti degil, senaryo planlama girisidir.
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

# OZEL SIRALAMA agirliklari: rejime gore dinamik. Ayi gununde tavan
# potansiyeli tamamen devre disi kalir; kâr alma agirligi domine eder.
RANK_WEIGHTS: Dict[str, Dict[str, float]] = {
    "STRONG_BULL":     {"profit_take": 0.45, "plus5": 0.35, "ceiling": 0.20},
    "BULL":            {"profit_take": 0.50, "plus5": 0.32, "ceiling": 0.18},
    "NEUTRAL":         {"profit_take": 0.55, "plus5": 0.30, "ceiling": 0.15},
    "HIGH_VOLATILITY": {"profit_take": 0.70, "plus5": 0.25, "ceiling": 0.05},
    "BEAR":            {"profit_take": 0.85, "plus5": 0.15, "ceiling": 0.00},
    "STRONG_BEAR":     {"profit_take": 1.00, "plus5": 0.00, "ceiling": 0.00},
}


def get_rank_weights(regime: str) -> Dict[str, float]:
    """Rejime gore ozel siralama agirliklarini dondurur."""
    return dict(RANK_WEIGHTS.get(str(regime or "").upper(), RANK_WEIGHTS["NEUTRAL"]))


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
