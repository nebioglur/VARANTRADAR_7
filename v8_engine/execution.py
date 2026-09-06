from typing import Dict, Any

class ExecutionEngine:
    """
    V8 Execution & Avoid Engine
    İyi bir hisse bulunsa bile "Şu an girilir mi?" sorusunu yanıtlar.
    Aşırı uzamış, direnci çok yakın veya riskli işlemlerde uyarır.
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
        rsi = breakout_data.get("metrics", {}).get("rsi", 50)
        
        status = "NO_ENTRY"
        reasons = []
        
        # 1. Temel Ret Kriterleri (Avoid Engine)
        if f_risk >= 50:
            reasons.append("High Fakeout Risk (>50%)")
            return self._build_result(symbol, "NO_ENTRY", reasons, "HIGH_RISK")
            
        if market_regime in ["STRONG_BEAR"] and b_score < 70:
            reasons.append("Market is too bearish for average breakouts")
            return self._build_result(symbol, "NO_ENTRY", reasons, "MARKET_REGIME")
            
        # 2. Aşırı Uzama / Kovalama Riski (Chase Risk)
        if rsi > 80:
            status = "CHASE_RISK"
            reasons.append(f"Price is heavily overbought (RSI: {rsi})")
            
        # 3. Pullback Bekleme
        elif rsi > 70 and b_score < 60:
            status = "WAIT_PULLBACK"
            reasons.append("Momentum is high but breakout lacks absolute strength. Wait for retest.")
            
        # 4. Temiz Giriş (Enter)
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
                
        return self._build_result(symbol, status, reasons, "OK")
        
    def _build_result(self, symbol, status, reasons, risk_level):
        return {
            "symbol": symbol,
            "entry_status": status,
            "reasons": reasons,
            "risk_profile": risk_level
        }
        
    def _default_result(self, reason):
        return {
            "symbol": "UNKNOWN",
            "entry_status": "NO_ENTRY",
            "reasons": [reason],
            "risk_profile": "UNKNOWN"
        }
