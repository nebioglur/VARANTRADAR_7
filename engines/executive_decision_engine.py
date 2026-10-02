from typing import Dict, Any
from engines.market_data_engine import MarketDataEngine
from engines.technical_engine import TechnicalEngine
from engines.smart_money_engine import SmartMoneyEngine
from engines.market_regime_engine import MarketRegimeEngine
from engines.fundamental_engine import FundamentalEngine
from engines.sentiment_engine import SentimentEngine

class ExecutiveDecisionEngine:
    """
    Modül 94: Executive Decision Engine.
    Sistemdeki tüm alt motorlardan (Teknik, Temel, Makro, Sentiment, Smart Money)
    verileri toplar, ağırlıklandırır ve tek bir "Nihai Karar" (Consensus) üretir.
    Hata töleranslıdır; bir motor çökse bile diğerleriyle karar üretmeye devam eder.
    """
    
    @staticmethod
    def generate_executive_decision(symbol: str, macro_symbol: str = "XU100.IS") -> Dict[str, Any]:
        result = {
            "Symbol": symbol,
            "Scores": {},
            "Final_Decision": "BEKLE",
            "Confidence_Score": 0,
            "Executive_Summary": ""
        }
        
        md = MarketDataEngine()
        
        # 1. Teknik Analiz (Ağırlık: %30)
        tech_score = 50
        tech_status = "NÖTR"
        try:
            df = md.fetch_data(symbol, period="1y", interval="1d")
            if not df.empty:
                tech = TechnicalEngine.calculate_all(df)
                if tech['Trend_Status'] == "UPTREND": tech_score = 80; tech_status = "GÜÇLÜ"
                elif tech['Trend_Status'] == "DOWNTREND": tech_score = 20; tech_status = "ZAYIF"
        except: pass
        
        # 2. Smart Money (Ağırlık: %20)
        sm_score = 50
        sm_status = "NÖTR"
        try:
            if not df.empty:
                sm = SmartMoneyEngine.analyze_smart_money(df)
                if "STRONG_BUY" in sm['Signal']: sm_score = 90; sm_status = "GİRİŞ VAR"
                elif "STRONG_SELL" in sm['Signal']: sm_score = 10; sm_status = "ÇIKIŞ VAR"
        except: pass
        
        # 3. Fundamental / Bilanço (Ağırlık: %25)
        fund_score = 50
        fund_status = "NÖTR"
        try:
            fund = FundamentalEngine.analyze_fundamentals(symbol)
            fund_score = fund['Fundamental_Score']
            fund_status = fund['Status']
        except: pass
        
        # 4. Sentiment / Haber (Ağırlık: %15)
        sent_score = 50
        sent_status = "NÖTR"
        try:
            sent = SentimentEngine.analyze_news(symbol)
            sent_score = sent['Sentiment_Score']
            sent_status = sent['Status']
        except: pass
        
        # 5. Market Regime / Makro (Ağırlık: %10 - Genel çarpana etki eder)
        macro_regime = "YATAY"
        try:
            df_macro = md.fetch_data(macro_symbol, period="1y", interval="1d")
            if not df_macro.empty:
                regime_data = MarketRegimeEngine.analyze_regime(df_macro)
                macro_regime = regime_data['Regime']
        except: pass
        
        # --- Ağırlıklı Hesaplama ---
        weighted_score = (tech_score * 0.30) + (fund_score * 0.25) + (sm_score * 0.20) + (sent_score * 0.15) + (50 * 0.10) # Makro için nötr 50 ekledik
        
        # Makro Ceza/Ödül (Eğer piyasa ayıysa, alım kararı zayıflar)
        if macro_regime == "AYI (BEAR)":
            weighted_score -= 10
        elif macro_regime == "BOĞA (BULL)":
            weighted_score += 10
            
        final_score = max(0, min(100, weighted_score))
        
        # Nihai Karar
        if final_score >= 70:
            decision = "GÜÇLÜ AL (STRONG BUY)"
            summary = "Teknik trendler yukarı, temel rasyolar sağlam ve haber akışı pozitif. Kurumsal (Smart Money) girişler gözlemleniyor. Alım yönlü risk alınabilir."
        elif final_score >= 55:
            decision = "AL (BUY)"
            summary = "Piyasa koşulları ve hisse metrikleri genel olarak olumlu. Kademeli alım düşünülebilir."
        elif final_score <= 30:
            decision = "GÜÇLÜ SAT (STRONG SELL)"
            summary = "Hem teknik olarak düşüş trendinde hem de temel (bilanço) veya haber akışında ciddi sıkıntılar var. Uzak durulmalı."
        elif final_score <= 45:
            decision = "SAT / RİSKİ AZALT (REDUCE)"
            summary = "Hisse metrikleri zayıflıyor. Portföyde ağırlık azaltılması mantıklı olabilir."
        else:
            decision = "TUT / BEKLE (HOLD)"
            summary = "Net bir yön yok. Teknik ve temel analizler birbiriyle çelişiyor veya piyasa bekle-gör modunda."
            
        result["Scores"] = {
            "Technical": {"Score": tech_score, "Status": tech_status},
            "Smart_Money": {"Score": sm_score, "Status": sm_status},
            "Fundamental": {"Score": fund_score, "Status": fund_status},
            "Sentiment": {"Score": sent_score, "Status": sent_status},
            "Macro_Regime": {"Score": "N/A", "Status": macro_regime}
        }
        
        result["Final_Decision"] = decision
        result["Confidence_Score"] = round(final_score, 1)
        result["Executive_Summary"] = summary
        
        return result
