import pandas as pd
from typing import Dict, Any, List

# Ajanları dahil ediyoruz
from .agents.trend_agent import TrendAgent
from .agents.volume_agent import VolumeAgent
from .agents.smart_money_agent import SmartMoneyAgent
from .agents.risk_agent import RiskAgent

class MultiAgentCoordinator:
    """
    Tüm uzman ajanları masaya toplar, veriyi onlara verir,
    oylarını (Vote) ve tartışmalarını (Reason) alır.
    Sonra bir 'Consensus (Ortak Karar)' çıkarır.
    """
    
    def __init__(self):
        self.agents = [
            TrendAgent(),
            VolumeAgent(),
            SmartMoneyAgent(),
            RiskAgent()
        ]
        
    def run_debate(self, df: pd.DataFrame, context: Dict[str, Any]) -> Dict[str, Any]:
        """Ajanları çalıştırıp oylarını toplar ve nihai kararı verir."""
        if df.empty or context is None:
            return {"Consensus": "VERİ YOK", "Debate_Log": []}
            
        debate_log = []
        total_vote_score = 0
        total_confidence = 0
        
        # 1. Ajanların Fikirlerini Al
        for agent in self.agents:
            response = agent.analyze(df, context)
            
            debate_log.append({
                "Agent": agent.name,
                "Role": agent.role,
                "Vote": response["Vote"],
                "Reason": response["Reason"],
                "Confidence": response["Confidence"]
            })
            
            # Risk ajanı gibi özel ajanların oyu, kararı direkt etkileyebilir. 
            # Basit Ağırlıklı Ortalama (Confidence'a göre ağırlık)
            total_vote_score += response["Vote"] * (response["Confidence"] / 100)
            total_confidence += response["Confidence"]
            
        # 2. Consensus (Ortak Karar) Çıkarımı
        # -1 ile +1 arasında bir değer dönecek
        avg_vote = total_vote_score / len(self.agents) 
        
        consensus_decision = "BEKLE / NÖTR"
        
        # Katı Kurallar (Veto hakkı)
        # Eğer Risk Ajanı Güçlü İtiraz ediyorsa (Vote == -1 ve Conf > 80), diğerleri ne derse desin riski belirtir.
        risk_agent_response = next((x for x in debate_log if x["Agent"] == "Risk Agent (Şeytanın Avukatı)"), None)
        
        if risk_agent_response and risk_agent_response["Vote"] == -1 and risk_agent_response["Confidence"] > 80:
            consensus_decision = "GÜÇLÜ RİSK VETOSU (SAT veya UZAK DUR)"
        else:
            # Standart Oylama Kararı
            if avg_vote > 0.4:
                consensus_decision = "GÜÇLÜ KONSENSÜS: AL"
            elif avg_vote > 0.15:
                consensus_decision = "KONSENSÜS: AL (İzlemeye Değer)"
            elif avg_vote < -0.4:
                consensus_decision = "GÜÇLÜ KONSENSÜS: SAT"
            elif avg_vote < -0.15:
                consensus_decision = "KONSENSÜS: SAT (Düzeltme Beklentisi)"
                
        return {
            "Consensus": consensus_decision,
            "Average_Vote_Score": round(avg_vote, 2),
            "Debate_Log": debate_log
        }
