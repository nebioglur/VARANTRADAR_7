"""V8 Backtest Motoru.

Geçmiş BIST verisi üzerinde V8 kırılım stratejisini test eder ve
başarım artırıcı filtrelerin (rejim kilidi + T+3 teyidi) gerçek
etkisini ölçer. 4 mod karşılaştırılır:

  A) HAM          : her ENTER sinyali alınır (eski davranış)
  B) +REJİM KİLİDİ: AYI/STRONG_AYI günlerinde girişler engellenir
  C) +TEYİT       : sinyal kapanışından sonra ertesi gün açılışı
                    negatif olmayan (teyit eden) işlemler alınır
  D) V8 PRO       : B + C birlikte

Sonuç /api/v8/backtest/result ucu ve V8 sayfasından okunur.
Ağır iş arka planda (daemon thread) çalışır; ana sunucuyu bloklamaz.
"""

import json
import math
import threading
import time
from datetime import datetime
from typing import Dict, Any, List

RESULT_FILE = "v8_backtest_result.json"

_STATE = {
    "status": "not_run",  # not_run | running | done | error
    "progress": 0,
    "message": "",
    "started_at": None,
    "finished_at": None,
    "result": None,
}
_LOCK = threading.Lock()


def get_state() -> dict:
    with _LOCK:
        return dict(_STATE)


def _load_previous():
    try:
        with open(RESULT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data and data.get("status") == "done":
            _STATE.update({"status": "done", "progress": 100,
                           "result": data.get("result"), "message": "Önceki backtest sonucu yüklendi",
                           "finished_at": data.get("finished_at")})
    except Exception:
        pass


_load_previous()


def _save_result(state_snapshot: dict):
    try:
        with open(RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump({"status": "done", "finished_at": state_snapshot.get("finished_at"),
                       "result": state_snapshot.get("result")}, f, ensure_ascii=False)
    except Exception:
        pass


def _ema(series, span: int):
    out = []
    k = 2.0 / (span + 1)
    prev = None
    for v in series:
        prev = v if prev is None else (v * k + prev * (1 - k))
        out.append(prev)
    return out


def _regime_label(xu_closes: List[float], idx: int) -> str:
    """XU100 kapanislarindan gunluk rejim yaklasimi (EMA50 + 5 gunluk yon)."""
    if idx < 55:
        return "NEUTRAL"
    win = xu_closes[max(0, idx - 50):idx + 1]
    e50 = _ema(win, 50)[-1]
    c = xu_closes[idx]
    c5 = xu_closes[idx - 5] if idx >= 5 else c
    if c > e50 and c5 > 0 and (c - c5) / c5 > 0.005:
        return "BULL"
    if c < e50 and c5 > 0 and (c - c5) / c5 < -0.005:
        return "BEAR"
    return "NEUTRAL"


def _simulate_trade(entry: float, stop_dist: float, t1_dist: float, t2_dist: float,
                    bars: List[dict]) -> dict:
    """Islemi sonraki gunluk barlarda yurutur: stop / hedef1 / hedef2 / 10 gun tutas."""
    stop = entry * (1 - stop_dist / 100.0)
    t1 = entry * (1 + t1_dist / 100.0)
    t2 = entry * (1 + t2_dist / 100.0)
    t1_hit = False
    for b in bars:
        low, high = b["low"], b["high"]
        if not t1_hit:
            if low <= stop:
                return {"result": "LOSS", "pct": -stop_dist}
            if high >= t2:
                return {"result": "WIN", "pct": t2_dist}
            if high >= t1:
                t1_hit = True
        else:
            if low <= stop:
                return {"result": "WIN", "pct": t1_dist}
            if high >= t2:
                return {"result": "WIN", "pct": t2_dist}
    last = bars[-1]["close"] if bars else entry
    pct = (last - entry) / entry * 100.0
    if pct > 0.5:
        return {"result": "WIN", "pct": pct}
    if pct < -0.5:
        return {"result": "LOSS", "pct": pct}
    return {"result": "NEUTRAL", "pct": pct}


def _aggregate(trades: List[dict]) -> dict:
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    decided = len(wins) + len(losses)
    gross_w = sum(t["pct"] for t in wins)
    gross_l = abs(sum(t["pct"] for t in losses))
    rets = [t["pct"] for t in trades]
    return {
        "count": len(trades),
        "win": len(wins),
        "loss": len(losses),
        "win_rate": round(100 * len(wins) / decided, 1) if decided else None,
        "avg_return": round(sum(rets) / len(rets), 2) if rets else None,
        "total_return": round(sum(rets), 2) if rets else None,
        "profit_factor": round(gross_w / gross_l, 2) if gross_l > 0 else None,
        "best": round(max(rets), 2) if rets else None,
        "worst": round(min(rets), 2) if rets else None,
    }


def run_backtest(symbols: List[str], days: int = 500):
    """Agir isi calistirir (arka plan thread'i icindendir)."""
    import pandas as _pd

    def _set(**kw):
        with _LOCK:
            _STATE.update(kw)

    _set(status="running", progress=2, message="Veriler indiriliyor (BIST + XU100)...",
         started_at=time.time(), result=None)
    try:
        import yfinance as yf
        from v8_engine.breakout import BreakoutEngine
        from v8_engine.execution import ExecutionEngine

        # XU100 coklu kaynak: baska sembol/deneme basarili olursa devam.
        idx_df = None
        for idx_sym in ("^XU100", "XU100.IS"):
            try:
                r = yf.download(idx_sym, period="2y", interval="1d", progress=False, timeout=20)
                if r is not None and not r.empty:
                    cand = r.dropna(how="all").copy()
                    if isinstance(cand.columns, _pd.MultiIndex):
                        cand.columns = [c[0] if isinstance(c, tuple) else c for c in cand.columns]
                    if "Close" in cand.columns and len(cand) > 60:
                        idx_df = cand
                        break
            except Exception:
                continue

        # 1. FAZ: tum sembol verilerini once indir (endeks yoksa evren vekili
        # uretmek icin kisilusturulmus kapanislarina ihtiyac var).
        dfs = {}
        for n_i, sym in enumerate(symbols):
            try:
                raw = yf.download(sym, period="2y", interval="1d", progress=False, timeout=20)
                if raw is None or raw.empty or len(raw) < 120:
                    continue
                d = raw.dropna(how="all").copy()
                if isinstance(d.columns, _pd.MultiIndex):
                    d.columns = [c[0] if isinstance(c, tuple) else c for c in d.columns]
                if "Close" in d.columns:
                    dfs[sym] = d
            except Exception:
                continue
            finally:
                _set(progress=5 + int(40 * (n_i + 1) / max(1, total)),
                     message=f"Veri indiriliyor: {sym} ({n_i + 1}/{total})")

        if idx_df is not None:
            xu_closes = [float(x) for x in idx_df["Close"].tolist()]
        else:
            # Endeks indirilemedi: evrenden esit agirlikli piyasa vekili uret
            # (sondan hizalanmis normalize kapanis ortalamasi). Backtest bunun
            # yerine calismayi REDDETMEZ; rejim etiketi yaklasik olur.
            norm = []
            for d in dfs.values():
                c = d["Close"].tolist()
                if len(c) >= 60:
                    base = c[0] if c[0] else 1.0
                    norm.append([v / base for v in c])
            if not norm:
                raise RuntimeError("Hisse verileri de indirilemedi; backtest yapilamadi")
            min_len = min(len(x) for x in norm)
            xu_closes = []
            for j in range(1, min_len + 1):
                xu_closes.append(sum(x[-j] for x in norm) / len(norm))
            xu_closes.reverse()
            _set(message="XU100 bulunamadi; evren vekili ile rejim yaklasimi kullanilacak")

        bo_engine = BreakoutEngine()
        ex_engine = ExecutionEngine()
        signals_by_mode = {"A": [], "B": [], "C": [], "D": []}
        total = len(symbols)

        # 2. FAZ: sinyal taramasi (veriler dfs'ten okunur, tekrar indirilmez)
        scan_i = 0
        for n_i, sym in enumerate(symbols):
            try:
                df = dfs.get(sym)
                if df is None or len(df) < 120:
                    continue
                scan_i += 1
                closes = df["Close"].tolist()
                opens = df["Open"].tolist()
                n = len(df)
                step = max(1, n // days) if days else 1
                for i in range(60, n - 11, step):
                    window = df.iloc[:i + 1]
                    regime = _regime_label(xu_closes, min(i, len(xu_closes) - 1))
                    bo = bo_engine.analyze_breakout(window, sym, regime)
                    if not bo or not bo.get("is_breakout"):
                        continue
                    ex = ex_engine.evaluate_entry(bo, regime)
                    if ex.get("entry_status") != "ENTER":
                        continue
                    sig_close = float(closes[i])
                    nxt_open = float(opens[i + 1]) if i + 1 < n else None
                    if not nxt_open or nxt_open <= 0:
                        continue
                    fwd = df.iloc[i + 1:i + 11]
                    bars = [{"open": float(r["Open"]), "high": float(r["High"]),
                             "low": float(r["Low"]), "close": float(r["Close"])}
                            for _, r in fwd.iterrows()]
                    try:
                        atr_pct = float((bo.get("metrics") or {}).get("atr_pct") or 0)
                    except (TypeError, ValueError):
                        atr_pct = 0.0
                    if atr_pct > 0:
                        stop_d = max(2.0, min(8.0, atr_pct * 1.5))
                        t1_d = max(2.0, min(10.0, atr_pct * 1.5))
                        t2_d = max(3.0, min(15.0, atr_pct * 2.5))
                    else:
                        stop_d, t1_d, t2_d = 5.0, 3.0, 5.0

                    trade = _simulate_trade(nxt_open, stop_d, t1_d, t2_d, bars)
                    trade.update({"symbol": sym, "date": str(window.index[-1])[:10],
                                  "regime": regime})
                    signals_by_mode["A"].append(dict(trade))
                    if regime not in ("BEAR", "STRONG_BEAR"):
                        signals_by_mode["B"].append(dict(trade))
                    if nxt_open >= sig_close:
                        signals_by_mode["C"].append(dict(trade))
                    if regime not in ("BEAR", "STRONG_BEAR") and nxt_open >= sig_close:
                        signals_by_mode["D"].append(dict(trade))
            except Exception:
                continue
            finally:
                _set(progress=45 + int(50 * scan_i / max(1, total)),
                     message=f"Taranıyor: {sym} ({n_i + 1}/{total})")

        labels = {
            "A": "A) Ham Sinyal (eski davranış)",
            "B": "B) + Rejim Kilidi (ayı piyasası engelli)",
            "C": "C) + Teyit Filtresi (açılış teyitli giriş)",
            "D": "D) V8 PRO (rejim kilidi + teyit)",
        }
        result = {
            "generated_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "symbols_tested": total,
            "modes": {k: {"label": labels[k], **_aggregate(v), "trades": v[:50]}
                      for k, v in signals_by_mode.items()},
        }
        _set(status="done", progress=100, message="Backtest tamamlandı",
             finished_at=time.time(), result=result)
        _save_result(dict(_STATE))
    except Exception as e:
        _set(status="error", progress=0, message=str(e), finished_at=time.time())


def start_backtest(symbols: List[str], days: int = 500) -> dict:
    """Backtest'i arka planda baslatir; zaten calisiyorsa mevcut durumu doner."""
    with _LOCK:
        if _STATE["status"] == "running":
            return {"status": "running", "progress": _STATE["progress"],
                    "message": _STATE["message"]}
        th = threading.Thread(target=run_backtest, args=(list(symbols), days), daemon=True)
        th.start()
        return {"status": "started"}
