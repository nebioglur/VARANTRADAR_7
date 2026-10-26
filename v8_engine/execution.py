from typing import Dict, Any

class ExecutionEngine:
    """
    V8 Execution & Avoid Engine
    İyi bir hisse bulunsa bile "Şu an girilir mi?" sorusunu yanıtlar.
    Kırılımın zaman çerçevesi (hız/momentum) ve çoklu periyot uyumuna göre karar verir.
    """
    ENTRY_STATUS_TR_MAP = {
        "ENTER": "GİRİŞ ONAYLI (AL)",
        "WAIT_PULLBACK": "RETEST BEKLE (GERİ ÇEKİLME)",
        "WAIT_CONFIRMATION": "TEYİT BEKLE",
        "CHASE_RISK": "AŞIRI YÜKSEK (KOVAMA)",
        "NO_ENTRY": "GİRİŞE UYGUN DEĞİL",
        "NO_SIGNAL": "SİNYAL YOK",
        "ERROR": "HATA"
    }

    SPEED_TR_MAP = {
        "EXPLOSIVE": "Çok Güçlü Patlama",
        "STRONG": "Güçlü Momentum",
        "NORMAL": "Normal",
        "WEAK": "Zayıf"
    }

    def __init__(self):
        pass
        
    def evaluate_entry(self, breakout_data: Dict[str, Any], market_regime: str) -> Dict[str, Any]:
        """
        Breakout Engine'den gelen verilere göre giriş kararı verir.
        """
        if not breakout_data or not breakout_data.get("is_breakout"):
            return self._default_result("SİNYAL YOK")

        symbol = breakout_data.get("symbol")
        b_score = breakout_data.get("breakout_score", 0.0)
        f_risk = breakout_data.get("fakeout_risk", 0.0)
        metrics = breakout_data.get("metrics", {})
        rsi = float(metrics.get("rsi", 50.0))
        rel_vol = float(metrics.get("relative_volume", 1.0))
        
        status = "NO_ENTRY"
        reasons = []
        timeframe_quality = 0.0
        
        # 1. Hız ve Momentum Hızı Analizi
        speed = "NORMAL"
        if rel_vol >= 1.8 and 50 <= rsi <= 78:
            speed = "EXPLOSIVE"
            timeframe_quality += 30.0
        elif rel_vol >= 1.3 and 48 <= rsi <= 80:
            speed = "STRONG"
            timeframe_quality += 20.0
        elif rel_vol >= 1.0:
            speed = "NORMAL"
            timeframe_quality += 10.0
        else:
            speed = "WEAK"
            reasons.append("Hacim desteği kırılım için zayıf")

        # 2. Temel Ret Kriterleri (Avoid Engine)
        change_pct = float(metrics.get("change_pct", 0.0))
        if change_pct >= 6.5:
            reasons.append("Hisse tavan seviyesinde (+%6.5+); alım kapalı / seans içi marj kalmadı.")
            return self._build_result(symbol, "NO_ENTRY", reasons, "TAVAN_RISK", 0.0, speed)

        if f_risk >= 60.0:
            reasons.append("Yüksek tuzak riski (>%60)")
            return self._build_result(symbol, "NO_ENTRY", reasons, "HIGH_RISK", timeframe_quality, speed)
            
        if market_regime in ["STRONG_BEAR"] and b_score < 60.0:
            reasons.append("Piyasa rejiminde sert satış baskısı var, sadece yüksek puanlı kırılımlar seçilir")
            return self._build_result(symbol, "NO_ENTRY", reasons, "MARKET_REGIME", timeframe_quality, speed)

        # 3. Aşırı Uzama / Kovalama Riski (Chase Risk)
        if rsi > 82.0:
            status = "CHASE_RISK"
            reasons.append(f"Fiyat aşırı alım bölgesinde (RSI: {rsi:.1f}), kovalamak riskli")
            timeframe_quality -= 15.0
            
        # 4. Pullback (Retest) Bekleme
        elif rsi > 70.0 and b_score < 65.0:
            status = "WAIT_PULLBACK"
            reasons.append("Momentum yüksek fakat direnç seviyesine geri çekilme (retest) beklenmeli")
            timeframe_quality -= 5.0
            
        # 5. Temiz Giriş (Enter)
        else:
            if b_score >= 48.0 and f_risk <= 45.0:
                status = "ENTER"
                reasons.append("Düşük tuzak riskli, güçlü kırılım onayı (AL)")
            elif b_score >= 38.0:
                status = "WAIT_CONFIRMATION"
                reasons.append("Kırılım hareketi başladı, hacim ve yön teyidi bekleniyor")
            else:
                status = "NO_ENTRY"
                reasons.append("Kırılım gücü giriş için yetersiz")
        
        timeframe_quality = max(0.0, min(100.0, timeframe_quality + b_score * 0.5 - f_risk * 0.25))
        
        return self._build_result(symbol, status, reasons, "OK", round(timeframe_quality, 1), speed)
        
    def _build_result(self, symbol, status, reasons, risk_level, timeframe_quality=0.0, speed="NORMAL"):
        return {
            "symbol": symbol,
            "entry_status": status,
            "entry_status_label": self.ENTRY_STATUS_TR_MAP.get(status, status),
            "reasons": reasons,
            "risk_profile": risk_level,
            "timeframe_quality": timeframe_quality,
            "momentum_speed": speed,
            "momentum_speed_label": self.SPEED_TR_MAP.get(speed, speed)
        }
        
    def _default_result(self, reason):
        return {
            "symbol": "UNKNOWN",
            "entry_status": "NO_ENTRY",
            "entry_status_label": self.ENTRY_STATUS_TR_MAP.get("NO_ENTRY", "NO_ENTRY"),
            "reasons": [reason],
            "risk_profile": "UNKNOWN",
            "timeframe_quality": 0.0,
            "momentum_speed": "NORMAL",
            "momentum_speed_label": "Normal"
        }
