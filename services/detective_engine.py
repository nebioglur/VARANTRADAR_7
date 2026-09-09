"""
PİYASA DEDEKTİFİ motoru.
Klasik indikatörler yerine davranışsal metrikler uretir:
anomali, hareket yasi, kirilma enerjisi, bilgi gecikmesi, kalabalik, tuzak,
piyasa rolu, parmak izi, firsat skoru + dedektif paneli (olay zinciri,
ayni gecmis, hisse karakteri, hareket zinciri).
Veri kaynagi: yfinance 5m (60 gun) + 1d (1 yil) barlari; XU100 benchmark.
"""
import threading
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Europe/Istanbul")
except ImportError:
    IST = None

from config.bist_symbols import BIST50_SYMBOLS, DOMINO_CLUSTERS

# Sembol evreni: BIST30 (hızlı + güvenilir) + sektör kümeleri
BIST30_SYMBOLS = [
    "AKBNK.IS", "ALARK.IS", "ASELS.IS", "BIMAS.IS", "EKGYO.IS", "EREGL.IS",
    "FROTO.IS", "GARAN.IS", "HEKTS.IS", "ISCTR.IS", "KCHOL.IS", "KOZAA.IS",
    "KOZAL.IS", "KRDMD.IS", "ODAS.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS",
    "SASA.IS", "SISE.IS", "TAVHL.IS", "TCELL.IS", "THYAO.IS", "TKFEN.IS",
    "TOASO.IS", "TUPRS.IS", "ULKER.IS", "VAKBN.IS", "VESTL.IS", "YKBNK.IS"
]
_ALL_CLUSTER = [m for members in DOMINO_CLUSTERS.values() for m in members]
SYMBOLS = [s for s in dict.fromkeys(BIST30_SYMBOLS + _ALL_CLUSTER) if s != "XU100.IS"]
BENCHMARK = "XU100.IS"

SECTOR_OF = {}
for _sec, _members in DOMINO_CLUSTERS.items():
    for _m in _members:
        SECTOR_OF.setdefault(_m, _sec)

_peer_changes = {}


def _now():
    if IST:
        return datetime.now(IST).replace(tzinfo=None)
    return datetime.now()


# ---------------------------------------------------------------- cache
_cache = {
    "rows": [],
    "summary": {},
    "built_at": None,
    "building": False,
    "error": None,
}
_data_store = {}   # sembol -> panel icin gereken hazir veriler
_lock = threading.Lock()
_build_lock = threading.Lock()

CACHE_TTL = 300  # saniye


def _dashboard_fallback(symbol):
    try:
        from server import GLOBAL_DASHBOARD_CACHE
        stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
        info = stats.get(symbol) or stats.get(symbol.replace(".IS", ""))
        if not isinstance(info, dict): return None
        price = info.get("Price") or info.get("Daily_Close")
        if price is None or pd.isna(price) or float(price) <= 0: return None
        return {"price": float(price), "change_pct": float(info.get("ChangePct") or info.get("Change_Pct") or 0)}
    except Exception:
        return None

def _fallback_row(sym, reason="Canlı veri bekleniyor"):
    quote = _dashboard_fallback(sym)
    if not quote: return None
    change = quote["change_pct"]; price = quote["price"]; sector = SECTOR_OF.get(sym, "GENEL")
    anomaly = int(min(100, max(0, 35 + abs(change) * 12)))
    energy = int(min(100, max(0, 25 + max(change, 0) * 10)))
    trap = int(min(100, max(0, abs(change) * 8)))
    status = "Hazırlık" if abs(change) < 1.2 else ("Hızlanıyor" if change > 1.2 else "Dağılım")
    opportunity = int(max(0, min(100, 45 + energy * .2 + anomaly * .2 - trap * .15)))
    return {"symbol": sym.replace(".IS", ""), "price": round(price, 2), "change_pct": round(change, 2), "sector": sector, "status": status, "anomaly": anomaly, "move_age": None, "energy": energy, "confirm": 0, "delay": 0, "crowd": int(min(100, abs(change) * 15)), "trap": trap, "role": "Takipçi", "fingerprint": "→→→→→→", "fingerprint_sim": None, "opportunity": opportunity, "opportunity_tag": "⚠️", "data_quality": "Günlük cache", "data_note": reason}


# ---------------------------------------------------------------- veri
def _download_5m(symbols):
    import yfinance as yf
    out = {}
    for i in range(0, len(symbols), 25):
        chunk = symbols[i:i + 25]
        try:
            data = yf.download(chunk, period="5d", interval="5m",
                               group_by="ticker", threads=False, progress=False, timeout=25)
        except Exception:
            continue
        if data is None or data.empty:
            continue
        for sym in chunk:
            try:
                df = data[sym].dropna(subset=["Close"]) if len(chunk) > 1 else data.dropna(subset=["Close"])
                if df is not None and len(df) > 30:
                    out[sym] = df
            except Exception:
                continue
    return out


def _download_1d(symbols):
    import yfinance as yf
    out = {}
    for i in range(0, len(symbols), 50):
        chunk = symbols[i:i + 50]
        try:
            data = yf.download(chunk, period="3mo", interval="1d",
                               group_by="ticker", threads=False, progress=False, timeout=25)
        except Exception:
            continue
        if data is None or data.empty:
            continue
        for sym in chunk:
            try:
                df = data[sym].dropna(subset=["Close"]) if len(chunk) > 1 else data.dropna(subset=["Close"])
                if df is not None and len(df) > 60:
                    out[sym] = df
            except Exception:
                continue
    return out


def _to_ist_index(df):
    df = df.copy()
    idx = pd.to_datetime(df.index)
    try:
        idx = idx.tz_convert("Europe/Istanbul").tz_localize(None)
    except Exception:
        pass
    df.index = idx
    return df


def _pivots(df5):
    """5m veriyi (gun x saat) matrislerine cevirir."""
    d = df5.copy()
    d["date"] = d.index.date
    d["slot"] = d.index.strftime("%H:%M")
    pv = {
        "open": d.pivot_table(index="date", columns="slot", values="Open"),
        "high": d.pivot_table(index="date", columns="slot", values="High"),
        "low": d.pivot_table(index="date", columns="slot", values="Low"),
        "close": d.pivot_table(index="date", columns="slot", values="Close"),
        "vol": d.pivot_table(index="date", columns="slot", values="Volume"),
    }
    for k in pv:
        pv[k] = pv[k].sort_index()
    return pv


def _sig(x, hi=0.7):
    """-1 / 0 / +1 imza degeri (z veya pct eşiğiyle)."""
    if pd.isna(x):
        return 0
    if x > hi:
        return 1
    if x < -hi:
        return -1
    return 0


def _z_vs_baseline(today_row, past_df):
    """Her slot icin (bugun - gecmis ort) / gecmis std."""
    mean = past_df.mean()
    std = past_df.std().replace(0, np.nan)
    return (today_row - mean) / std


def _fingerprint_from_row(day_open, day_close, day_high, day_low, day_vol, vol_z,
                          mom_ret, bench_ret, cutoff_slot=None):
    """6 harfli gun parmak izi: F H V M S L (↑ ↓ →)."""
    f = _sig((day_close - day_open) / max(day_open, 0.01) * 100, 0.5)
    rng = max(day_high - day_low, 0.01)
    h = _sig((day_close - day_low) / rng * 100 - 50, 20)
    v = _sig(vol_z, 0.7)
    m = _sig(mom_ret * 100, 0.6)
    s = 0  # S daha asagida vol bazli hesaplanir
    l = _sig(bench_ret, 0.5)
    return {"F": f, "H": h, "V": v, "M": m, "S": s, "L": l}


def _fp_match(a, b):
    keys = ["F", "H", "V", "M", "S", "L"]
    same = sum(1 for k in keys if a.get(k) == b.get(k))
    return round(100 * same / len(keys))


# ---------------------------------------------------------------- analiz
def _analyze(sym, df5, df1d, bench5, bench1d, now):
    pv = _pivots(df5)
    dates = list(pv["close"].index)
    if not dates:
        return None
    today = dates[-1]
    slots = list(pv["close"].columns)
    now_slot = now.strftime("%H:%M")
    live_slots = [s for s in slots if s <= now_slot] if today == now.date() else slots
    # Slot kolonlari gecmis gunlerden geliyor; bugunun o slotta verisi yoksa
    # (yfinance NaN/satir-dusuerturek) fiyat NaN olur. Sadece bugun gercekten
    # veri olan slotlarla calis.
    if today in pv["close"].index:
        today_close_all = pv["close"].loc[today]
        live_slots = [s for s in live_slots if pd.notna(today_close_all.get(s, np.nan))]
    if len(live_slots) < 4:
        return None

    t_close = pv["close"].loc[today, live_slots].astype(float)
    t_open = pv["open"].loc[today, live_slots].astype(float)
    t_high = pv["high"].loc[today, live_slots].astype(float)
    t_low = pv["low"].loc[today, live_slots].astype(float)
    t_vol = pv["vol"].loc[today, live_slots].astype(float)
    past_mask = [d for d in dates[:-1]][-45:]
    if len(past_mask) < 3:
        return None
    p_vol = pv["vol"].loc[past_mask, live_slots].astype(float)
    p_close = pv["close"].loc[past_mask, live_slots].astype(float)

    vol_z = _z_vs_baseline(t_vol, p_vol)
    px_ret = t_close.pct_change()
    ret_z = _z_vs_baseline(t_close.pct_change() * 100, p_close.pct_change() * 100)

    last_i = len(live_slots) - 1
    recent_vol_z = vol_z.iloc[-6:].max()
    px_z = ret_z.iloc[-6:].max()
    anomaly = 0.0
    for z in (recent_vol_z, px_z):
        if pd.notna(z):
            anomaly = max(anomaly, float(np.clip((z - 1.5) * 22 + 25, 0, 100)))

    # hareket baslangici: son 1.5 saatte ilk z>=2 barı
    anomaly_start_slot = None
    for j in range(max(0, last_i - 18), last_i + 1):
        z = vol_z.iloc[j]
        r = abs(float(px_ret.iloc[j]) * 100) if pd.notna(px_ret.iloc[j]) else 0
        if (pd.notna(z) and z >= 2.0) or r >= 1.2:
            anomaly_start_slot = live_slots[j]
            break
    move_age = None
    if anomaly_start_slot:
        h1, m1 = map(int, anomaly_start_slot.split(":"))
        t0 = now.replace(hour=h1, minute=m1, second=0, microsecond=0)
        move_age = max(0, int((now - t0).total_seconds() / 60))

    # vwap + degisim
    tp = (t_high + t_low + t_close) / 3
    cum_v = t_vol.cumsum()
    vwap = float((tp * t_vol).cumsum().iloc[-1] / max(cum_v.iloc[-1], 1))
    price = float(t_close.iloc[-1])
    day_open = float(t_open.iloc[0])
    day_high = float(t_high.max())
    day_low = float(t_low.min())
    if not (pd.notna(price) and pd.notna(day_open)) or price <= 0 or day_open <= 0:
        return None
    change_pct = (price - day_open) / max(day_open, 0.01) * 100

    # benchmark bugun
    bchg = 0.0
    if bench5 is not None and len(bench5):
        b = bench5[bench5.index.date == today] if hasattr(bench5.index, "date") else bench5
        if len(b) >= 2:
            bchg = (float(b["Close"].iloc[-1]) - float(b["Open"].iloc[0])) / float(b["Open"].iloc[0]) * 100

    # sektor
    sector = SECTOR_OF.get(sym, "GENEL")
    peers = [m for m in DOMINO_CLUSTERS.get(sector, []) if m != sym]

    # kirilma enerjisi (7 sart kontrol listesi)
    prev_high = None
    if len(dates) >= 2:
        prev = dates[-2]
        prev_high = float(pv["high"].loc[prev].max())
    conds = {
        "vwap_uzerinde": price > vwap,
        "acilis_range_kirildi": price > float(t_high.iloc[:max(3, len(live_slots) // 4)].max()),
        "hacim_artiyor": float(t_vol.iloc[-3:].mean()) > float(t_vol.mean()) * 1.3,
        "zirveye_yakin": price >= day_high * 0.995,
        "ust_uste_yesil": bool((px_ret.iloc[-3:] > 0).sum() >= 2),
        "momentum": float(px_ret.iloc[-6:].sum() * 100) > 0.8,
        "benchmark_pozitif": bchg > -0.2,
    }
    energy = round(100 * sum(conds.values()) / len(conds))

    # kirilim onayi: dunku zirve kirma ZORUNLU, vwap/hacim destegi guclendirir
    broke_prev_high = bool(prev_high and price > prev_high)
    if broke_prev_high:
        confirm = 100 if (price > vwap or conds["hacim_artiyor"]) else 66
    elif price > vwap and conds["hacim_artiyor"]:
        confirm = 33
    else:
        confirm = 0

    # dilatma / kalabalik
    ext_from_start = 0.0
    if anomaly_start_slot:
        try:
            start_px = float(t_close.loc[anomaly_start_slot])
            ext_from_start = (price - start_px) / max(start_px, 0.01) * 100
        except Exception:
            pass
    vol_fade = 0.0
    if recent_vol_z and pd.notna(recent_vol_z) and recent_vol_z >= 1:
        peak_vol = float(t_vol.max())
        vol_fade = max(0.0, 1 - float(t_vol.iloc[-3:].mean()) / max(peak_vol, 1))
    crowd = 0.0
    if move_age:
        crowd += min(50, move_age / 45 * 50)
    crowd += max(0.0, min(30, (ext_from_start - 1.5) * 15))
    crowd += vol_fade * 20 if price >= day_high * 0.99 else 0
    crowd = int(min(100, crowd))

    # tuzak bileşenleri
    trap, trap_items = 0, []
    res_ref = None
    if df1d is not None and len(df1d) >= 21:
        res_ref = float(df1d["High"].iloc[-21:-1].max())
    near_res = res_ref is not None and price >= res_ref * 0.99
    if near_res:
        trap += 25; trap_items.append("Üst direnç yakın")
    ext_vwap = (price - vwap) / max(vwap, 0.01) * 100
    if ext_vwap > 3:
        trap += 20; trap_items.append("VWAP'tan aşırı dilatma")
    gap_pct = (day_open - (float(df1d["Close"].iloc[-2]) if df1d is not None and len(df1d) >= 2 else day_open)) / max(day_open, 0.01) * 100
    if gap_pct > 4:
        trap += 15; trap_items.append("Açılışta büyük gap")
    if change_pct > 6:
        trap += 15; trap_items.append("Günde aşırı yükseliş (FOMO)")
    last_range = (float(t_high.iloc[-1]) - float(t_low.iloc[-1])) / max(price, 0.01) * 100
    if last_range > 2.5:
        trap += 10; trap_items.append("Son mumda geniş aralık")
    if crowd >= 60:
        trap += 15; trap_items.append("Yön kalabalıklaşmış")
    trap = int(min(100, trap))

    # bilgi gecikmesi: sektor bugun hareket etti, hisse geride
    delay = 0
    peer_changes = _peer_changes.get(sector, {})
    if peers and peer_changes:
        sec_mean = float(np.mean([v for v in peer_changes.values()]))
        if sec_mean >= 0.8 and change_pct < sec_mean - 0.4:
            delay = int(min(100, (sec_mean - change_pct) * 30))
    elif bchg >= 0.8 and change_pct < bchg - 0.4:
        delay = int(min(100, (bchg - change_pct) * 25))

    # rol
    role = "Takipçi"
    if peers and peer_changes:
        sec_mean = float(np.mean(list(peer_changes.values())))
        if change_pct > sec_mean + 1.0 and change_pct > 0.5:
            role = "Lider"
        elif change_pct < 0 and sec_mean > 1.0:
            role = "Zayıf Halka"
        elif delay >= 55:
            role = "Geciken"
        elif change_pct > sec_mean + 0.3:
            role = "Takipçi"
        else:
            role = "Uydu"
    else:
        if change_pct > bchg + 1.0 and change_pct > 0.5:
            role = "Lider"
        elif bchg > 1.0 and change_pct < 0.3:
            role = "Geciken"
        elif bchg < -1.0 and change_pct > 0.8:
            role = "Ters Hareket"

    # durum
    status = "Sessiz"
    if change_pct > 6 and (crowd >= 60 or ext_vwap > 5):
        status = "Aşırı"
    elif change_pct < -4 and anomaly >= 55:
        status = "Dağılım"
    elif trap >= 65 and confirm < 50:
        status = "Tuzak"
    elif confirm >= 66:
        status = "Kırılım"
    elif energy >= 70 and anomaly >= 40:
        status = "Hızlanıyor"
    elif anomaly_start_slot and move_age is not None and move_age <= 60 and change_pct > 0.8:
        status = "Hareket"
    elif energy >= 50 and anomaly >= 50 and abs(change_pct) < 1.5:
        status = "Hazırlık"
    elif anomaly >= 65:
        status = "Anormal"

    # parmak izi (bugun - kesikli) + gecmis gunlerle kiyas
    day_vol_total = float(t_vol.sum())
    past_day_vol = pv["vol"].loc[past_mask].sum(axis=1).astype(float)
    vol_z_day = (day_vol_total - past_day_vol.mean()) / (past_day_vol.std() or 1)
    mom_ret = float(px_ret.iloc[-6:].sum()) if len(px_ret) >= 6 else 0.0
    fp_today = _fingerprint_from_row(day_open, price, day_high, day_low, day_vol_total,
                                     vol_z_day, mom_ret, bchg)
    rng = max(day_high - day_low, 0.01)
    fp_today["S"] = 1 if last_range > 1.2 else (-1 if last_range < 0.4 else 0)

    similar = []
    b1d = bench1d
    for d in past_mask[-30:]:
        cols = [s for s in live_slots if s in pv["close"].columns]
        c = pv["close"].loc[d, cols].astype(float).dropna()
        o = pv["open"].loc[d, cols].astype(float).dropna()
        h = pv["high"].loc[d, cols].astype(float).dropna()
        lo = pv["low"].loc[d, cols].astype(float).dropna()
        v = pv["vol"].loc[d, cols].astype(float).dropna()
        if len(c) < max(4, len(live_slots) // 2):
            continue
        vwap_d = float(((h + lo + c) / 3 * v).cumsum().iloc[-1] / max(v.sum(), 1))
        price_d = float(c.iloc[-1])
        open_d = float(o.iloc[0])
        chg_d = (price_d - open_d) / max(open_d, 0.01) * 100
        # benchmark ayni gun ayni saat
        bd = 0.0
        if bench5 is not None:
            bb = bench5[bench5.index.date == d]
            if len(bb) >= 2:
                bd = (float(bb["Close"].iloc[-1]) - float(bb["Open"].iloc[0])) / float(bb["Open"].iloc[0]) * 100
        rng_d = float(h.max()) - float(lo.min())
        pos_d = (price_d - float(lo.min())) / max(rng_d, 0.01) * 100
        fp = {
            "F": _sig(chg_d, 0.5),
            "H": _sig(pos_d - 50, 20),
            "V": 0, "M": 0, "S": 0,
            "L": _sig(bd, 0.5),
        }
        sim = _fp_match(fp_today, fp)
        if sim >= 67:
            # sonraki 60dk ya da sonraki gun getirisi
            fut = None
            if d in dates:
                full = pv["close"].loc[d].astype(float).dropna()
                later = full[full.index > cols[-1]]
                if len(later) >= 2 and cols[-1] < "17:00":
                    fut = (float(later.iloc[min(len(later) - 1, 12)]) - float(later.iloc[0])) / float(later.iloc[0]) * 100
                    fut_label = "Sonraki 60dk"
            if fut is None and df1d is not None:
                di = list(df1d.index)
                tgt = None
                for k, ix in enumerate(di):
                    if ix.date() == d:
                        tgt = k
                        break
                if tgt is not None and tgt + 1 < len(di):
                    fut = (float(df1d["Close"].iloc[tgt + 1]) - float(df1d["Close"].iloc[tgt])) / float(df1d["Close"].iloc[tgt]) * 100
                    fut_label = "Sonraki gün"
            if fut is not None:
                similar.append({"date": str(d), "sim": sim,
                                "outcome": round(fut, 2), "label": fut_label})
    similar.sort(key=lambda x: -x["sim"])
    similar = similar[:5]
    pos_sim = [s["outcome"] for s in similar if s["outcome"] > 0]
    bias = "Belirsiz"
    if similar:
        bias = "Pozitif eğilim" if len(pos_sim) >= len(similar) / 2 else "Negatif eğilim"

    # firsat skoru
    opp = 0.28 * energy + 0.22 * anomaly + 0.18 * (100 - crowd) + 0.18 * (100 - trap) + 0.14 * (100 - delay)
    opp = int(min(100, max(0, opp)))
    if status in ("Sessiz", "VERİ YOK"):
        opp = min(opp, 55)

    row = {
        "symbol": sym.replace(".IS", ""),
        "price": round(price, 2),
        "change_pct": round(change_pct, 2),
        "sector": sector,
        "status": status,
        "anomaly": int(anomaly),
        "move_age": move_age,
        "energy": energy,
        "confirm": confirm,
        "delay": delay,
        "crowd": crowd,
        "trap": trap,
        "role": role,
        "fingerprint": "".join({"-1": "↓", "1": "↑", "0": "→"}[str(fp_today[k])] for k in ["F", "H", "V", "M", "S", "L"]),
        "fingerprint_sim": similar[0]["sim"] if similar else None,
        "opportunity": opp,
        "opportunity_tag": "🔥" if opp >= 85 else ("✅" if opp >= 70 else ("⚠️" if opp < 55 else "•")),
    }

    _data_store[sym] = {
        "row": row,
        "pv": {k: v for k, v in pv.items()},
        "today": today,
        "live_slots": live_slots,
        "vol_z": vol_z,
        "ret_z": ret_z,
        "px_ret": px_ret,
        "vwap": vwap,
        "price": price,
        "day_open": day_open,
        "day_high": day_high,
        "day_low": day_low,
        "prev_high": prev_high,
        "conds": conds,
        "trap_items": trap_items,
        "sector": sector,
        "peers": peers,
        "similar": similar,
        "bias": bias,
        "df1d": df1d,
        "anomaly_start_slot": anomaly_start_slot,
        "change_pct": change_pct,
        "bchg": bchg,
        "ext_vwap": ext_vwap,
        "role": role,
        "crowd": crowd,
        "delay": delay,
        "energy": energy,
        "anomaly": anomaly,
        "gap_pct": gap_pct,
    }
    return row


# ---------------------------------------------------------------- panel
def _timeline(sym):
    d = _data_store.get(sym)
    if not d:
        return []
    pv = d["pv"]
    slots = d["live_slots"]
    events = []
    vol_z = d["vol_z"]
    px_ret = d["px_ret"]
    tp_vol = pv["vol"].loc[d["today"], slots].astype(float)

    started = {"vol": False, "flow": False, "volat": False, "high": False, "break": False, "mom": False}
    cum_flow = 0.0
    mean_range = None
    for i, s in enumerate(slots):
        c = pv["close"].loc[d["today"], s]
        o = pv["open"].loc[d["today"], s]
        h = pv["high"].loc[d["today"], s]
        lo = pv["low"].loc[d["today"], s]
        v = tp_vol.iloc[i]
        if pd.isna(c):
            continue
        rng_pct = (float(h) - float(lo)) / max(float(c), 0.01) * 100
        if mean_range is None and i >= 6:
            mean_range = tp_vol.iloc[:i].std()
        if not started["vol"] and pd.notna(vol_z.iloc[i]) and vol_z.iloc[i] >= 2.0:
            events.append((s, "Anormal hacim başladı", "🟢"))
            started["vol"] = True
        if not started["flow"]:
            cum_flow += (1 if float(c) >= float(o) else -1) * float(v)
            if cum_flow > 0 and float(v) > 0:
                events.append((s, "Para akışı pozitife döndü", "🟢"))
                started["flow"] = True
        if not started["volat"] and rng_pct > 1.2 and i >= 3:
            events.append((s, "Normal volatilite aşıldı", "🟡"))
            started["volat"] = True
        if not started["high"] and float(h) >= d["day_high"] * 0.995 and i >= 3:
            events.append((s, "Günün zirvesi test edildi", "🟡"))
            started["high"] = True
        if not started["break"] and d["prev_high"] and float(c) > d["prev_high"]:
            events.append((s, "Direnç kırıldı (dünkü yüksek)", "🔵"))
            started["break"] = True
        if not started["mom"] and i >= 6 and float(px_ret.iloc[i - 5:i + 1].sum()) * 100 > 1.2:
            events.append((s, "Momentum hızlandı", "🔵"))
            started["mom"] = True
    events.sort(key=lambda x: x[0])
    return [{"time": t, "text": txt, "kind": k} for t, txt, k in events]


def _character(sym):
    d = _data_store.get(sym)
    df = d.get("df1d") if d else None
    if df is None or len(df) < 60:
        return None
    r = df["Close"].pct_change().dropna() * 100
    volat = float(min(100, r.std() / 0.06 * 100))
    big = r[r > 3]
    ani = float(min(100, (r.abs() > 4).mean() * 100 * 3))
    fake = 0.0
    if len(big) > 3:
        nxt = r.shift(-1).loc[big.index]
        fake = float(min(100, (nxt < 0).mean() * 100 * 1.6))
    retest = 0.0
    if len(big) > 3:
        hit = []
        for ix in big.index:
            i = list(df.index).index(ix)
            if i + 1 < len(df):
                hit.append(df["High"].iloc[i + 1] >= df["Close"].iloc[i])
        retest = float(min(100, np.mean(hit) * 100)) if hit else 0.0
    cont = 0.0
    if len(big) > 3:
        nxt = r.shift(-1).loc[big.index].dropna()
        cont = float((nxt > 0).mean() * 100)
    hizli = 0.0
    pv5 = d["pv"]["high"]
    htimes, total = 0, 0
    for day in pv5.index[-40:]:
        row = pv5.loc[day].astype(float).dropna()
        if row.empty:
            continue
        total += 1
        hi_slot = row.idxmax()
        if hi_slot <= "12:00":
            htimes += 1
    if total:
        hizli = round(100 * htimes / total)
    return {
        "ani_patlama": int(ani),
        "hizli": hizli,
        "sahte_kirilim": int(fake),
        "retest": int(retest),
        "trend_devam": int(cont),
        "volatilite": int(volat),
    }


def _chain(sym):
    d = _data_store.get(sym)
    if not d:
        return {"sector": d["sector"] if d else "GENEL", "members": [], "next": []}
    sector = d["sector"]
    members = []
    nxt = []
    for m in _data_store:
        md = _data_store[m]
        if md["sector"] != sector or m == sym:
            continue
        r = md["row"]
        members.append({"symbol": m.replace(".IS", ""), "change_pct": r["change_pct"],
                        "anomaly": r["anomaly"], "status": r["status"]})
        if r["anomaly"] >= 50 and abs(r["change_pct"]) < 1.0:
            nxt.append(m.replace(".IS", ""))
    members.sort(key=lambda x: -x["change_pct"])
    return {"sector": sector, "members": members, "next": nxt[:3]}


def get_detail(symbol):
    sym = symbol.strip().upper()
    if not sym.endswith(".IS"):
        sym += ".IS"
    d = _data_store.get(sym)
    if not d:
        return None
    row = d["row"]
    timeline = _timeline(sym)
    character = _character(sym)
    chain = _chain(sym)

    why = []
    if row["anomaly"] >= 60:
        why.append(("🟢", "Hacim anomalisi: işlem davranışı normalin çok üzerinde"))
    if row["role"] == "Lider":
        why.append(("🟢", "Sektör liderliği: sektörünün bugünkü performansından belirgin önde"))
    if row["delay"] < 30 and row["anomaly"] >= 50:
        why.append(("🟢", "Bilgi gecikmesi düşük: fiyat, hacim sinyalini henüz tam yansıtmadı"))
    if row["energy"] >= 70:
        why.append(("🟢", "Kırılım enerjisi yüksek: şartların çoğu oluşmuş durumda"))
    if row["confirm"] >= 66:
        why.append(("🔵", "Kırılım onaylandı: dünkü zirve hacimle aşıldı"))
    if row["crowd"] >= 50:
        why.append(("🟡", "Kalabalık artıyor: hareket olgunlaşmış, geç giriş riski var"))
    if row["delay"] >= 55:
        why.append(("🟡", "Geciken aday: sektör/emsaller hareket etti, bu hisse henüz geride"))
    for item in d["trap_items"]:
        why.append(("🔴", f"Tuzak riski: {item}"))
    if not why:
        why.append(("⚪", "Belirgin bir davranışsal sinyal yok — sessiz izleme modu"))

    return {
        "symbol": row["symbol"],
        "row": row,
        "timeline": timeline,
        "start_point": timeline[0]["time"] if timeline else d["anomaly_start_slot"],
        "why": why,
        "similar": d["similar"],
        "bias": d["bias"],
        "character": character,
        "chain": chain,
    }


# ---------------------------------------------------------------- ozet
def _build():
    now = _now()
    print("[DEDEKTIF] Veri indiriliyor...")
    all_syms = SYMBOLS + [BENCHMARK]
    d5 = _download_5m(all_syms)
    d1 = _download_1d(all_syms)
    bench5 = _to_ist_index(d5[BENCHMARK]) if BENCHMARK in d5 else None
    bench1d = _to_ist_index(d1[BENCHMARK]) if BENCHMARK in d1 else None

    global _peer_changes
    _peer_changes = {}
    today = None
    # sektor ortalamalari icin once ham degisimler
    raw_change = {}
    for sym in SYMBOLS:
        df5 = d5.get(sym)
        if df5 is None:
            continue
        df5 = _to_ist_index(df5)
        dates = sorted(set(df5.index.date))
        if not dates:
            continue
        t = dates[-1]
        td = df5[df5.index.date == t]
        if len(td) < 4:
            continue
        chg = (float(td["Close"].iloc[-1]) - float(td["Open"].iloc[0])) / max(float(td["Open"].iloc[0]), 0.01) * 100
        raw_change[sym] = chg
    for sec, members in DOMINO_CLUSTERS.items():
        vals = {m: raw_change[m] for m in members if m in raw_change}
        if vals:
            _peer_changes[sec] = vals

    rows = []
    for sym in SYMBOLS:
        df5 = d5.get(sym)
        try:
            if df5 is not None:
                r = _analyze(sym, _to_ist_index(df5),
                             _to_ist_index(d1[sym]) if sym in d1 else None,
                             bench5, bench1d, now)
            else:
                r = _fallback_row(sym, "5 dakikalık veri sağlayıcısı yanıt vermedi")
            if r:
                rows.append(r)
        except Exception as e:
            print(f"[DEDEKTIF] {sym} analiz hatasi: {e}")
            r = _fallback_row(sym, "Canlı analiz geçici olarak kullanılamıyor")
            if r:
                rows.append(r)

    rows.sort(key=lambda r: -r["opportunity"])
    summary = {
        "anomaly": len([r for r in rows if r["anomaly"] >= 70]),
        "energy": len([r for r in rows if r["energy"] >= 70 and r["confirm"] < 66]),
        "quiet": len([r for r in rows if r["status"] == "Hazırlık" or (r["change_pct"] < 1 and r["anomaly"] >= 60)]),
        "delayed": len([r for r in rows if r["delay"] >= 60]),
        "trap": len([r for r in rows if r["trap"] >= 60]),
        "leader": len([r for r in rows if r["role"] == "Lider"]),
        "breakout": len([r for r in rows if r["status"] == "Kırılım"]),
        "total": len(rows),
    }
    with _lock:
        _cache["rows"] = rows
        _cache["summary"] = summary
        _cache["built_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
        _cache["building"] = False
        _cache["error"] = None
    print(f"[DEDEKTIF] Tamamlandi: {len(rows)} hisse, {now.strftime('%H:%M')}")


def start_build():
    if _build_lock.acquire(blocking=False):
        def _run():
            try:
                _build()
            except Exception as e:
                import traceback
                err = traceback.format_exc()
                print(f"[DEDEKTIF] HATA: {e}\n{err}")
                with _lock:
                    _cache["building"] = False
                    _cache["error"] = str(e)
            finally:
                _build_lock.release()
        threading.Thread(target=_run, daemon=True).start()
        return True
    return False


def get_rows():
    """UI icin satirlar; cache bos ise arka plan insasi tetikler."""
    with _lock:
        if _cache["rows"] and _cache["built_at"]:
            age = (datetime.now() - datetime.strptime(_cache["built_at"], "%Y-%m-%d %H:%M:%S")).total_seconds()
        else:
            age = None
        building = _cache["building"]
    if age is None and not building:
        start_build()
        return {"status": "building", "rows": [], "summary": {}, "built_at": None}
    if age is not None and age > CACHE_TTL and not building:
        start_build()
    with _lock:
        return {
            "status": "ok" if _cache["rows"] else "building",
            "rows": _cache["rows"],
            "summary": _cache["summary"],
            "built_at": _cache["built_at"],
            "error": _cache["error"],
        }


def start_background_loop():
    """Her 5 dakikada bir tazele (piyasa acikken); kapaliyken 30 dk'da bir."""
    def _loop():
        while True:
            try:
                with _lock:
                    age = None
                    if _cache["built_at"]:
                        age = (datetime.now() - datetime.strptime(_cache["built_at"], "%Y-%m-%d %H:%M:%S")).total_seconds()
                need = age is None or age > CACHE_TTL
                if need:
                    start_build()
            except Exception:
                pass
            time.sleep(300)
    threading.Thread(target=_loop, daemon=True).start()
