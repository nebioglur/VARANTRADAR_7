import pandas as pd
from services.analyzer import Analyzer
from utils.logger import logger

class ScoringEngine:
    def __init__(self):
        self.analyzer = Analyzer()

    def generate_score(self, symbol: str, interval: str = "1d") -> dict:
        """
        Generates a confidence score (0-100) and reasoning (Buy/Sell/Wait)
        based on advanced technical, trend, and volume indicators.
        """
        logger.info(f"Running ScoringEngine for {symbol} ({interval})")
        df = self.analyzer.calculate_indicators(symbol, interval)
        
        if df.empty or len(df) < 50:
            return {
                "symbol": symbol,
                "score": 0,
                "action": "BEKLE",
                "reasoning": "Yeterli veri bulunamadı."
            }
            
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        score = 50 # Base score
        reasons = []
        
        # 1. RSI Logic (Weight: 10)
        rsi = latest.get('RSI', 50)
        if rsi < 30:
            score += 10
            reasons.append("RSI aşırı satım bölgesinde (AL sinyali).")
        elif rsi > 70:
            score -= 10
            reasons.append("RSI aşırı alım bölgesinde (SAT sinyali).")
            
        # 2. MACD Logic (Weight: 10)
        macd = latest.get('MACD', 0)
        macd_signal = latest.get('MACD_Signal', 0)
        if macd > macd_signal and prev['MACD'] <= prev['MACD_Signal']:
            score += 10
            reasons.append("MACD yukarı yönlü kesişim yaptı (AL sinyali).")
        elif macd < macd_signal and prev['MACD'] >= prev['MACD_Signal']:
            score -= 10
            reasons.append("MACD aşağı yönlü kesişim yaptı (SAT sinyali).")
            
        # 3. Trend Score & Strength Logic (Weight: 20)
        trend_score = latest.get('Trend_Score', 0)
        adx = latest.get('ADX_14', 0)
        if trend_score >= 2:
            score += 15
            reasons.append(f"Güçlü Yükseliş Trendi (Trend Skoru: {trend_score}/3).")
            if adx > 25:
                score += 5
                reasons.append(f"ADX ({adx:.1f}) trendin güçlü olduğunu doğruluyor.")
        elif trend_score <= -2:
            score -= 15
            reasons.append(f"Güçlü Düşüş Trendi (Trend Skoru: {trend_score}/3).")
            if adx > 25:
                score -= 5
                reasons.append(f"ADX ({adx:.1f}) düşüş trendini doğruluyor.")
                
        # 4. Volume & Money Flow Logic (Weight: 15)
        vol_change = latest.get('Vol_Change_Pct', 100)
        money_flow = latest.get('Money_Flow_Status', 'Neutral')
        if vol_change > 150: # Volume is 50% above average
            if money_flow == "Inflow" and latest['close'] > prev['close']:
                score += 15
                reasons.append("Yüksek hacimli yükseliş ve para girişi saptandı (AL).")
            elif money_flow == "Outflow" and latest['close'] < prev['close']:
                score -= 15
                reasons.append("Yüksek hacimli düşüş ve para çıkışı saptandı (SAT).")
                
        # 5. Support / Resistance (Weight: 15)
        close_price = latest['close']
        pivot = latest.get('Pivot', close_price)
        s1 = latest.get('S1', 0)
        r1 = latest.get('R1', float('inf'))
        
        # Check if price is bouncing off support or hitting resistance
        if close_price > s1 and prev['close'] <= s1:
            score += 15
            reasons.append(f"Fiyat S1 desteğinden ({s1:.2f}) sekti (Güçlü AL sinyali).")
        elif close_price < r1 and prev['close'] >= r1:
            score -= 15
            reasons.append(f"Fiyat R1 direncinden ({r1:.2f}) döndü (SAT sinyali).")
            
        # Normalize score between 0 and 100
        score = max(0, min(100, score))
        
        action = "BEKLE"
        if score >= 75:
            action = "AL"
        elif score <= 35:
            action = "SAT"
            
        result = {
            "symbol": symbol,
            "interval": interval,
            "score": score,
            "action": action,
            "reasoning": "\n".join([f"- {r}" for r in reasons])
        }
        
        logger.info(f"Score for {symbol} ({interval}): {score}/100 -> {action}")
        return result

if __name__ == "__main__":
    scorer = ScoringEngine()
    print(scorer.generate_score("ASELS.IS"))
