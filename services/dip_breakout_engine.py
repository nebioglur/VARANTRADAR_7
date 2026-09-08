"""
DİP & KIRILIM RADARI motoru.
Akıllı dip tespiti (10 kriter) + 3 aşamalı kırılım analizi
(YAKLAŞIYOR / DENEME / ONAYLANDI) + tuzak riski + dip-kırılım mesafesi.
Kategoriler: EN ERKEN DİPLER, DİP→KIRILIM, KIRILIM→MOMENTUM.
Veri kaynagi: yfinance 1d (6 ay) gunluk barlari; XU100 benchmark.
"""
import threading
import time
from datetime import datetime

import numpy as np
import pandas as pd

from services.detective_engine import SYMBOLS, SECTOR_OF, DOMINO_CLUSTERS, BENCHMARK

_cache = {
    "rows": [],
    "summary": {},
    "built_at": None,
    "building": False,
    "error": None,
}
_lock = threading.Lock()
_build_lock = threading.Lock()

CACHE_TTL = 300  # saniye


def get_rows():
    """Cache'den satirlari dondurur; bos/bayat ise arka plan insasi tetikler."""
    _maybe_build()
    with _lock:
        return {
            "rows": _cache["rows"],
            "summary": _cache["summary"],
            "built_at": _cache["built_at"],
            "error": _cache["error"],
        }


def _maybe_build():
    with _lock:
        built_at = _cache["built_at"]
        building = _cache["building"]
    stale = built_at is None or (datetime.now() - built_at).total_seconds() > CACHE_TTL
    if (stale or _cache["error"]) and not building:
        t = threading.Thread(target=_build, daemon=True)
        t.start()


def start_background_loop():
    def _loop():
        while True:
            try:
                _build()
            except Exception:
                pass
            time.sleep(CACHE_TTL)
    # tek seferlik baslatma
    if not getattr(start_background_loop, "_started", False):
        start_background_loop._started = True
        t = threading.Thread(target=_loop, daemon=True)
        t.start()


# ---------------------------------------------------------------- veri
def _download_1d(symbols):
    import yfinance as yf
    out = {}
    for i in range(0, len(symbols), 50):
        chunk = symbols[i:i + 50]
        try:
            data = yf.download(chunk, period="6mo", interval="1d",
                               group_by="ticker", threads=False, progress=False, timeout=30)
        except Exception:
            continue
        if data is None or data.empty:
            continue
        for sym in chunk:
            try:
                df = data[sym].dropna(subset=["Close"]) if len(chunk) > 1 else data.dropna(subset=["Close"])
                if df is not None and len(df) > 40:
                    out[sym] = df
            except Exception:
                continue
    return out


# ---------------------------------------------------------------- yardimcilar
def _swing_lows(lows, w=3):
    """Yerel dipler (window w'lik yerel minimum)."""
    out = []
    n = len(lows)
    for i in range(w, n - w):
        win = lows[i - w:i + w + 1]
        if lows[i] == min(win):
            out.append((i, lows[i]))
    # tekrar eden dipleri temizle (ayni deger ard ardina)
    dedup = []
    for i, v in out:
        if dedup and abs(dedup[-1][1] - v) / max(v, .01) < 0.001 and i - dedup[-1][0] <= w:
            continue
        dedup.append((i, v))
    return dedup


def _obv(close, volume):
    direction = np.sign(np.diff(close, prepend=close[0]))
    return np.cumsum(direction * volume)


# ---------------------------------------------------------------- analiz
def _analyze(sym, df, bench, sector_ret5, bench_ret5_now, bench_ret5_prev):
    if df is None or len(df) < 40:
        return None
    d = df.copy()
    if isinstance(d.columns[0], tuple):
        return None
    close = d["Close"].astype(float).values
    high = d["High"].astype(float).values
    low = d["Low"].astype(float).values
    vol = d["Volume"].astype(float).values
    n = len(close)
    price = float(close[-1])
    if price <= 0:
        return None

    prev_close = float(close[-2]) if n >= 2 else price
    change_pct = (price - prev_close) / max(prev_close, .01) * 100

    ret = np.diff(close) / close[:-1] * 100  # gunluk % getiri (n-1)

    # --- temel bolgeler
    win20 = slice(max(0, n - 21), n - 1)  # onceki 20 gun (bugun haric)
    resistance = float(np.max(high[win20]))
    dip_price = float(np.min(low[max(0, n - 30):]))
    dist_to_res = (resistance - price) / price * 100
    from_dip = (price - dip_price) / max(dip_price, .01) * 100

    avg_vol20 = float(np.mean(vol[win20])) if n > 21 else float(np.mean(vol))
    vol_today = float(vol[-1])

    # --- 10 kriterli dip analizi
    checks = {}

    # 1) Satis baskisi azaliyor: dusus gunlerinin hacmi geride kalana gore azaliyor
    down_mask = ret < 0
    idx = np.arange(len(ret))
    recent5 = idx[-5:]
    prior10 = idx[-15:-5]
    dv_recent = [abs(ret[i]) * vol[i + 1] for i in recent5 if down_mask[i]]
    dv_prior = [abs(ret[i]) * vol[i + 1] for i in prior10 if down_mask[i]]
    checks["satis_azaldi"] = (len(dv_recent) < 3 and (not dv_prior or (np.mean(dv_recent) if dv_recent else 0) < np.mean(dv_prior) * 1.1)) or len(dv_recent) <= 1

    # 2) Yeni dipler daha dusuk mu: son 10 gunde dip kirmadi
    low_10 = float(np.min(low[-10:]))
    low_prev = float(np.min(low[max(0, n - 30):max(0, n - 10)])) if n > 15 else low_10
    checks["dip_tutundu"] = low_10 >= low_prev * 0.995

    # 3) Hacim kuruyor
    vol5 = float(np.mean(vol[-5:]))
    checks["hacim_kuruyor"] = vol5 > avg_vol20 * 1.05

    # 4) Para cikisi durdu: OBV egimi dususunden duzluge/yukselise gecti
    obv = _obv(close, vol)
    obv_slope_now = float(obv[-1] - obv[-6])
    obv_slope_prev = float(obv[-11] - obv[-16]) if n > 16 else obv_slope_now
    checks["para_cikisi_durdu"] = obv_slope_now > obv_slope_prev * 0.8

    # 5) Volatilite dusuyor
    vola_now = float(np.std(ret[-5:]))
    vola_prev = float(np.std(ret[-15:-5])) if len(ret) >= 15 else vola_now
    checks["volatilite_dustu"] = vola_now < vola_prev

    # 6) Destek bolgesinde tepki: 20g dipine yakin ve son kapanis dipten yukarda
    low20 = float(np.min(low[max(0, n - 20):]))
    near_support = (price - low20) / max(low20, .01) * 100 < 4.0
    bounce = (close[-1] - low[-1]) / max(low[-1], .01) * 100 > 1.0
    checks["destek_tepki"] = near_support and bounce

    # 7) Sektor toparlaniyor
    checks["sektor_toparliyor"] = sector_ret5 is not None and sector_ret5 > -1.5

    # 8) Endekse gore zayiflik sona eriyor: goreceli guc iyilesiyor
    if bench_ret5_now is not None and bench_ret5_prev is not None:
        r5_now = float(close[-1] / close[-6] * 100 - 100) if n >= 6 else 0
        r5_prev = float(close[-6] / close[-11] * 100 - 100) if n >= 11 else r5_now
        rel_now = r5_now - bench_ret5_now
        rel_prev = r5_prev - bench_ret5_prev
        checks["endeks_zayiflik_bitti"] = rel_now > rel_prev - 0.5
    else:
        checks["endeks_zayiflik_bitti"] = False

    # 9) Dip sonrasi ilk higher-low
    sl = _swing_lows(list(low[-45:]), w=3)
    checks["higher_low"] = len(sl) >= 2 and sl[-1][1] > sl[-2][1] * 0.998

    # 10) Ayni bolgede gecmiste tepki: dip bolgesi daha once test edilip toparlanmis
    zone_top = dip_price * 1.02
    reacted = 0
    for i in range(max(0, n - 60), n - 5):
        if low[i] <= zone_top and close[i] > low[i] * 1.015:
            reacted += 1
            if reacted >= 2:
                break
    checks["gecmis_tepki"] = reacted >= 2

    # agirliklar: davranis donum noktasi kriterleri daha degerli
    weights = {
        "satis_azaldi": 1.0,
        "dip_tutundu": 1.5,
        "hacim_kuruyor": 1.2,
        "para_cikisi_durdu": 1.2,
        "volatilite_dustu": 1.0,
        "destek_tepki": 1.2,
        "sektor_toparliyor": 0.8,
        "endeks_zayiflik_bitti": 0.8,
        "higher_low": 1.5,
        "gecmis_tepki": 1.0,
    }
    total_w = sum(weights.values())
    dip_pct = int(round(sum(weights[k] for k, v in checks.items() if v) / total_w * 100))

    # --- kirilim asamasi
    obv_up = obv_slope_now > 0
    range_today = max(high[-1] - low[-1], .01)
    close_pos = (close[-1] - low[-1]) / range_today  # 0..1
    factors = 0
    if vol_today >= avg_vol20 * 1.5:
        factors += 1
    if close_pos >= 0.7:
        factors += 1
    if obv_up:
        factors += 1
    if change_pct > 1.0:
        factors += 1

    if price > resistance:
        stage = "ONAYLANDI" if factors >= 3 else "DENEME"
    elif dist_to_res <= 3.0:
        stage = "YAKLAŞIYOR"
    else:
        stage = "UZAK"

    # --- tuzak riski (5 faktor x 20)
    trap = 0
    if vol_today < avg_vol20 * 1.2:
        trap += 20  # hacim zayif
    upper_wick = (high[-1] - max(close[-1], prev_close)) / range_today
    if upper_wick > 0.40:
        trap += 20  # ust fitil yuksek
    if obv_slope_now < 0:
        trap += 20  # para akisi negatif
    high60 = float(np.max(high[max(0, n - 60):]))
    if (high60 - price) / price * 100 <= 3.0:
        trap += 20  # ust zaman dilimi direnci cok yakin
    if price > resistance * 1.04:
        trap += 20  # kirilimdan cok uzaklasmis / gec kalınmis

    # --- islem onerisi
    if trap >= 60:
        action = "BEKLE ⚠️"
    elif stage == "ONAYLANDI" and dist_to_res < -5.0:
        action = "GEÇ KALMIŞ"  # kirilim coktan gerceklesmis, uzaklasilmis
    elif stage == "ONAYLANDI" and trap <= 40:
        action = "AL"
    elif stage == "DENEME" and trap <= 40:
        action = "İZLE"
    elif dip_pct >= 75 and from_dip <= 5:
        action = "DİP AVI"
    else:
        action = "BEKLE"

    # --- kategori
    category = None
    if stage == "ONAYLANDI":
        category = "MOMENTUM"
    elif stage in ("YAKLAŞIYOR", "DENEME") and dip_pct >= 50:
        category = "DIP_KIRILIM"
    elif dip_pct >= 65 and from_dip <= 6:
        category = "ERKEN_DIP"

    # dip + kirilim esigi
    threshold = 2.0 <= from_dip <= 8.0 and dist_to_res <= 2.5 and dist_to_res >= 0

    # firsat skoru: dip gucu + kirilima yakinlik - tuzak
    proximity = max(0, 100 - abs(dist_to_res) * 25) if dist_to_res >= 0 else 40
    opportunity = int(max(0, min(100, dip_pct * .45 + proximity * .35 - trap * .25)))
    if category == "MOMENTUM":
        opportunity = int(max(0, min(100, opportunity + 10)))

    sector = SECTOR_OF.get(sym, "GENEL")
    return {
        "symbol": sym.replace(".IS", ""),
        "price": round(price, 2),
        "change_pct": round(change_pct, 2),
        "sector": sector,
        "stage": stage,
        "dip_pct": dip_pct,
        "dip_checks": checks,
        "dip_price": round(dip_price, 2),
        "from_dip_pct": round(from_dip, 2),
        "resistance": round(resistance, 2),
        "dist_to_res_pct": round(dist_to_res, 2),
        "trap_pct": trap,
        "action": action,
        "category": category,
        "threshold_tag": threshold,
        "opportunity": opportunity,
    }


# ---------------------------------------------------------------- insa
def _build():
    with _build_lock:
        with _lock:
            if _cache["building"]:
                return
            _cache["building"] = True
        try:
            syms = list(SYMBOLS)
            data = _download_1d(syms + [BENCHMARK])
            bench = data.get(BENCHMARK)

            # benchmark 5g getirisi (simdiki ve onceki pencere)
            bench_ret5_now = bench_ret5_prev = None
            if bench is not None and len(bench) >= 11:
                c = bench["Close"].astype(float).values
                bench_ret5_now = float(c[-1] / c[-6] * 100 - 100)
                bench_ret5_prev = float(c[-6] / c[-11] * 100 - 100)

            # sektor 5g ortalama getiri
            sector_ret5 = {}
            for sec, members in DOMINO_CLUSTERS.items():
                rets = []
                for m in members:
                    dfm = data.get(m)
                    if dfm is not None and len(dfm) >= 6:
                        cm = dfm["Close"].astype(float).values
                        rets.append(float(cm[-1] / cm[-6] * 100 - 100))
                sector_ret5[sec] = float(np.mean(rets)) if rets else None

            rows = []
            for sym in syms:
                try:
                    r = _analyze(sym, data.get(sym), bench, sector_ret5.get(SECTOR_OF.get(sym, "GENEL")),
                                 bench_ret5_now, bench_ret5_prev)
                    if r:
                        rows.append(r)
                except Exception:
                    continue

            rows.sort(key=lambda x: -x["opportunity"])
            summary = {
                "erken_dip": sum(1 for r in rows if r["category"] == "ERKEN_DIP"),
                "dip_kirilim": sum(1 for r in rows if r["category"] == "DIP_KIRILIM"),
                "momentum": sum(1 for r in rows if r["category"] == "MOMENTUM"),
                "total": len(rows),
            }
            with _lock:
                _cache["rows"] = rows
                _cache["summary"] = summary
                _cache["built_at"] = datetime.now()
                _cache["error"] = None if rows else "Veri üretilemedi (yfinance yanıt vermedi)"
        except Exception as e:
            with _lock:
                _cache["error"] = str(e)
        finally:
            with _lock:
                _cache["building"] = False
