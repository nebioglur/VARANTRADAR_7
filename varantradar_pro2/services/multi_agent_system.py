import random
from services.llm_advisor import LLMAdvisor

class MultiAgentSystem:
    """
    VarantRadar X (V12) - Multi-Agent AI Kurulu
    Trend AI, Risk AI ve Macro AI'ın veriyi tartışıp Supervisor AI'a sunduğu yapı.
    """
    def __init__(self):
        self.llm = LLMAdvisor()

    def run_agent_council(self, symbol: str, ai_report: dict) -> dict:
        """Karar kurulunu toplar ve ajanları konuşturur."""
        
        # Gerçek bir sistemde bu 4 ajan ayrı LLM prompları (persona) ile çalışır.
        # Token/zaman tasarrufu için tek çağrıda simüle ediyoruz veya local logic kullanıyoruz.
        
        score = ai_report.get('Total_Score', 50)
        
        # 1. Trend AI
        trend_opinion = "AL" if score > 55 else "SAT" if score < 45 else "BEKLE"
        trend_reason = f"Trend indikatörleri pozitif uyumsuzluk gösteriyor." if trend_opinion == "AL" else "Trend zayıf, satıcılar baskın."
        
        # 2. Risk AI
        risk_opinion = "SAT" if ai_report.get('Volatility', 50) > 70 else "BEKLE" if score < 60 else "AL"
        risk_reason = "Volatilite kabul edilebilir seviyede, risk/ödül oranı makul." if risk_opinion == "AL" else "Aşırı oynaklık var, sermaye koruma moduna geçilmeli."
        
        # 3. Macro AI (Smart Money)
        macro_opinion = "AL" if "Yükseliş" in ai_report.get('AI_Comment', '') else "SAT"
        macro_reason = "Para akışı sektörel olarak bu hisseyi destekliyor." if macro_opinion == "AL" else "Makroekonomik rüzgarlar bu varlık sınıfının tersine esiyor."
        
        opinions = [trend_opinion, risk_opinion, macro_opinion]
        al_votes = opinions.count("AL")
        sat_votes = opinions.count("SAT")
        
        # Supervisor AI (Yönetici YZ)
        if al_votes >= 2:
            final_decision = "GÜÇLÜ AL"
            supervisor_note = f"Kurul {al_votes} AL oyu ile alım yönünde uzlaştı. Risk AI'ın uyarıları limitli pozisyonla tolere edilebilir."
        elif sat_votes >= 2:
            final_decision = "GÜÇLÜ SAT"
            supervisor_note = f"Kurul {sat_votes} SAT oyu ile satış yönünde uzlaştı. Portföy korumaya alınmalı."
        else:
            final_decision = "PAS GEÇ (BEKLE)"
            supervisor_note = "Ajanlar arasında derin fikir ayrılıkları (Conflict) mevcut. Uzlaşma sağlanamadığı için nakitte kalınmalı."
            
        return {
            "Trend_AI": {"Vote": trend_opinion, "Reason": trend_reason},
            "Risk_AI": {"Vote": risk_opinion, "Reason": risk_reason},
            "Macro_AI": {"Vote": macro_opinion, "Reason": macro_reason},
            "Supervisor": {"Decision": final_decision, "Note": supervisor_note, "Confidence": max(al_votes, sat_votes) * 33}
        }
