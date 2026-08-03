import pandas as pd
from typing import Dict, Any, List

from engines.market_data_engine import MarketDataEngine
from engines.technical_engine import TechnicalEngine
from engines.smart_money_engine import SmartMoneyEngine
from engines.volume_analytics_engine import VolumeAnalyticsEngine
from engines.smart_ai_engine import SmartAI_Engine
from engines.multi_agent_coordinator import MultiAgentCoordinator

class AutonomousRadar:
    """
    Belirlenen hisse havuzunu (Örn: BIST30 veya kullanıcının listesi) otonom olarak tarar.
    Her hisse için Multi-Agent (Çoklu Ajan) toplantısı düzenler.
    Konsensüs sağlanan (Örn: GÜÇLÜ AL) hisseleri filtreleyip Fırsat Skoru'na göre sıralar.
    """
    
    @staticmethod
    def scan_market(symbols: List[str], period: str = "1y", interval: str = "1d") -> Dict[str, Any]:
        opportunities = []
        md = MarketDataEngine()
        coordinator = MultiAgentCoordinator()
        
        for sym in symbols:
            df = md.fetch_data(sym, period=period, interval=interval)
            if df.empty:
                continue
                
            # Ajanların kullanacağı contexti hazırla
            tech = TechnicalEngine.calculate_all(df)
            sm_res = SmartMoneyEngine.analyze_smart_money(df)
            vol_res = VolumeAnalyticsEngine.analyze_volume(df)
            ai_insight = SmartAI_Engine.generate_ai_insight(df)
            
            context = {
                "tech": tech,
                "sm": sm_res,
                "vol": vol_res,
                "wyckoff": ai_insight.get("Wyckoff_Phase", "UNKNOWN"),
                "mani_risk": ai_insight.get("Manipulation_Analysis", {}).get("Risk_Score", 0)
            }
            
            # Ajanları toplantıya çağır ve kararı al
            debate_res = coordinator.run_debate(df, context)
            
            consensus = debate_res.get("Consensus", "")
            score = debate_res.get("Average_Vote_Score", 0)
            
            # Sadece "AL" veya "GÜÇLÜ AL" kararı çıkanları listeye ekle
            if "AL" in consensus:
                opportunities.append({
                    "Symbol": sym,
                    "Consensus": consensus,
                    "AI_Score": score, # -1 ile +1 arası
                    "Opportunity_Score": round(score * 100, 1) if score > 0 else 0, # Yüzdelik fırsat skoru
                    "Wyckoff": ai_insight.get("Wyckoff_Phase", ""),
                    "Smart_Money": sm_res.get('Smart_Money_Score', 50)
                })
                
        # Fırsat skoruna göre (Yüksekten düşüğe) sırala
        opportunities = sorted(opportunities, key=lambda x: x["Opportunity_Score"], reverse=True)
        
        return {
            "Total_Scanned": len(symbols),
            "Opportunities_Found": len(opportunities),
            "Results": opportunities
        }
