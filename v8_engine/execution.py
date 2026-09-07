from typing import Dict, Any

class ExecutionEngine:
    """
    V8 Execution & Avoid Engine
    İyi bir hisse bulunsa bile "Şu an girilir mi?" sorusunu yanıtlar.
    Artık kırılımın zaman çerçevesi (hız/momentum) ve çoklu periyot uyumuna
    göre karar verir.
    """
    def __init__(self):
        pass
        
    def evaluate_entry(self, breakout_data: Dict[str, Any], market_regime: str) -> Dict[str, Any]:
        """
        Breakout Engine'den gelen verilere göre giriş kararı verir.
        """
        if not breakout_data or not breakout_data.get("is_breakout"):
            return self._default_result("NO_SIGNAL")

        symbol = breakout_data.get("symbol")
        b_score = breakout_data.get("breakout_score", 0)
        f_risk = breakout_data.get("fakeout_risk", 0)
        metrics = breakout_data.get("metrics", {})
        rsi = metrics.get("rsi", 50)
        rel_vol = metrics.get("relative_volume", 1.0)
        
        status = "NO_ENTRY"
        reasons = []
        timeframe_quality = 0
        
        # 1. Temel Ret Kriterleri (Avoid Engine)
        if f_risk >= 50:
            reasons.append("High Fakeout Risk (>50%)")
            return self._build_result(symbol, "NO_ENTRY", reasons, "HIGH_RISK", timeframe_quality)
            
        if market_regime in ["STRONG_BEAR"] and b_score < 70:
            reasons.append("Market is too bearish for average breakouts")
            return self._build_result(symbol, "NO_ENTRY", reasons, "MARKET_REGIME", timeframe_quality)
        
        # 2. Zaman Çerçevesi / Momentum Hızı Analizi
        # Hacim ve RSI'ye göre kırılımın "hızını" sınıflandırır
        speed = "NORMAL"
        if rel_vol > 2.0 and 55 <= rsi <= 70:
            speed = "EXPLOSIVE"
            timeframe_quality += 30
        elif rel_vol > 1.5 and 50 <= rsi <= 75:
            speed = "STRONG"
            timeframe_quality += 20
        elif rel_vol >= 1.0:
            speed = "NORMAL"
            timeframe_quality += 10
        else:
            speed = "WEAK"
            reasons.append("Low volume speed for this breakout")
        
        # 3. Aşırı Uzama / Kovalama Riski (Chase Risk)
        if rsi > 80:
            status = "CHASE_RISK"
            reasons.append(f"Price is heavily overbought (RSI: {rsi})")
            timeframe_quality -= 15
            
        # 4. Pullback Bekleme
        elif rsi > 70 and b_score < 60:
            status = "WAIT_PULLBACK"
            reasons.append("Momentum is high but breakout lacks absolute strength. Wait for retest.")
            timeframe_quality -= 5
            
        # 5. Temiz Giriş (Enter)
        else:
            if b_score >= 60 and f_risk <= 30:
                status = "ENTER"
                reasons.append("Strong Breakout with low fakeout risk.")
            elif b_score >= 40:
                status = "WAIT_CONFIRMATION"
                reasons.append("Breakout started but needs more volume/time confirmation.")
            else:
                status = "NO_ENTRY"
                reasons.append("Breakout score is too weak.")
        
        timeframe_quality = max(0, min(100, timeframe_quality + b_score * 0.5 - f_risk * 0.3))
        
        return self._build_result(symbol, status, reasons, "OK", round(timeframe_quality, 1), speed)
        
    def _build_result(self, symbol, status, reasons, risk_level, timeframe_quality=0.0, speed="NORMAL"):
        return {
            "symbol": symbol,
            "entry_status": status,
            "reasons": reasons,
            "risk_profile": risk_level,
            "timeframe_quality": timeframe_quality,
            "momentum_speed": speed
        }
        
    def _default_result(self, reason):
        return {
            "symbol": "UNKNOWN",
            "entry_status": "NO_ENTRY",
            "reasons": [reason],
            "risk_profile": "UNKNOWN",
            "timeframe_quality": 0.0,
            "momentum_speed": "-"
        }
