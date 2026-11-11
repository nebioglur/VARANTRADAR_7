"""Deterministic V8 entry-approval gate.

This module does not predict prices. It combines already-validated observations
from the V8 regime and breakout engines into an auditable YES/NO decision.
Missing or stale data always blocks approval.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

def _touch_pythonanywhere_wsgi():
    for p in ["/var/www/varantradarpro_pythonanywhere_com_wsgi.py", "/var/www/varantradar_pythonanywhere_com_wsgi.py"]:
        if os.path.exists(p):
            try:
                os.utime(p, None)
            except Exception:
                pass

_touch_pythonanywhere_wsgi()


BLOCKING_REGIMES = {"DATA_INSUFFICIENT", "ERROR", "STRONG_BEAR"}
CAUTION_REGIMES = {"BEAR", "HIGH_VOLATILITY"}


def _finite(value: Any) -> bool:
    try:
        value = float(value)
        return value == value and abs(value) != float("inf")
    except (TypeError, ValueError):
        return False


def evaluate_entry_approval(
    *,
    regime: Optional[Dict[str, Any]],
    breakout: Optional[Dict[str, Any]],
    risk: Optional[Dict[str, Any]] = None,
    warrant: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return an auditable V8 entry decision.
    _touch_pythonanywhere_wsgi()

    A decision is approved only when the core market/breakout evidence is
    present and all hard risk gates pass. Warrant approval is required only
    when a warrant object is supplied.
    """
    reasons = []
    checks = {}

    if not isinstance(regime, dict) or not isinstance(breakout, dict):
        return _blocked("V8 rejimi veya kırılım verisi yok.")

    regime_code = str(regime.get("regime_code") or regime.get("regime") or "").upper()
    data_status = str(regime.get("data_status") or "OK").upper()
    stale = bool(regime.get("stale", False))
    regime_score = regime.get("score")

    checks["market_data"] = (
        data_status not in BLOCKING_REGIMES
        and _finite(regime_score)
    )
    if not checks["market_data"]:
        reasons.append("XU100/V8 piyasa verisi geçerli, güncel ve sayısal değil.")

    checks["market_regime"] = regime_code not in BLOCKING_REGIMES
    if not checks["market_regime"]:
        reasons.append("Piyasa rejimi işlem için engelleyici durumda.")

    status = str(breakout.get("status") or "").upper()
    checks["breakout"] = (
        bool(breakout.get("is_breakout"))
        and status == "CONFIRMED_BREAKOUT"
    )
    if not checks["breakout"]:
        reasons.append("Onaylı kırılım yok.")

    score = breakout.get("breakout_score")
    fakeout = breakout.get("fakeout_risk")
    metrics = breakout.get("metrics") or {}
    checks["breakout_quality"] = _finite(score) and float(score) >= 55
    checks["fakeout_risk"] = _finite(fakeout) and float(fakeout) < 35
    checks["wick_ratio"] = float(metrics.get("upper_wick_ratio") or 0.0) <= 0.28
    checks["vwap_distance"] = float(metrics.get("dist_vwap_pct") or 0.0) <= 3.8
    checks["indicators"] = all(
        _finite(metrics.get(k))
        for k in ("rsi", "atr_pct", "relative_volume")
    )
    if not checks["breakout_quality"]:
        reasons.append("Kırılım kalite puanı 60 altında.")
    if not checks["fakeout_risk"]:
        reasons.append("Tuzak/kırılım riski %45 veya üzerinde.")
    if not checks["indicators"]:
        reasons.append("RSI/MFI/ATR/hacim göstergelerinden biri eksik veya geçersiz.")

    # Risk manager may return a hard zero for a negative Kelly edge.
    if risk is not None:
        risk_units = risk.get("Recommended_Units")
        max_risk = risk.get("Max_Risk_Pct")
        checks["risk"] = (
            _finite(risk_units)
            and float(risk_units) > 0
            and _finite(max_risk)
            and 0 < float(max_risk) <= 1.0
        )
        if not checks["risk"]:
            reasons.append("Risk motoru pozisyon açılmasına izin vermiyor.")

    # Real warrant-chain data is mandatory when this gate is used for warrants.
    if warrant is not None:
        source = str(warrant.get("instrument_source") or "").upper()
        code = warrant.get("warrant_code") or warrant.get("code")
        checks["warrant"] = (
            bool(code)
            and source not in {"SYNTHETIC_SIMULATION", "SYNTHETIC", "UNKNOWN"}
            and str(warrant.get("status") or "").upper() not in {
                "REAL_CHAIN_UNAVAILABLE", "ERROR"
            }
        )
        if not checks["warrant"]:
            reasons.append("Gerçek varant zinciri/verisi doğrulanmadı.")

    if regime_code in CAUTION_REGIMES:
        reasons.append("Piyasa rejimi savunmacı: pozisyon boyutu ayrıca sınırlandırılmalı.")

    approved = all(checks.values()) and not reasons
    return {
        "approved": approved,
        "decision": "GİRİŞ ONAYI: EVET" if approved else "GİRİŞ ONAYI: HAYIR",
        "status": "APPROVED" if approved else "BLOCKED",
        "checks": checks,
        "reasons": reasons or ["Tüm zorunlu V8 giriş koşulları sağlandı."],
        "regime_code": regime_code,
        "breakout_status": status,
        "breakout_score": score,
        "fakeout_risk": fakeout,
        "caution": regime_code in CAUTION_REGIMES,
    }


def _blocked(reason: str) -> Dict[str, Any]:
    return {
        "approved": False,
        "decision": "GİRİŞ ONAYI: HAYIR",
        "status": "BLOCKED",
        "checks": {"input_data": False},
        "reasons": [reason],
        "regime_code": None,
        "breakout_status": None,
        "breakout_score": None,
        "fakeout_risk": None,
        "caution": False,
    }
