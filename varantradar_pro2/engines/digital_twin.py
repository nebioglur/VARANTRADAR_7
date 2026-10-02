import pandas as pd
import datetime
from typing import Dict, Any

from engines.market_data_engine import MarketDataEngine
from engines.technical_engine import TechnicalEngine
from engines.smart_money_engine import SmartMoneyEngine
from engines.volume_analytics_engine import VolumeAnalyticsEngine
from engines.smart_ai_engine import SmartAI_Engine
from engines.multi_agent_coordinator import MultiAgentCoordinator

class DigitalTwinSandbox:
    """
    Geçmiş bir tarihteki piyasa koşullarını simüle eder (Historical Replay).
    Veriyi o tarihten sonrasını bilmeyecek şekilde keser (Time Machine).
    Ajanları bu kesilmiş veriyle test ederek "O gün ne karar verirdik?" sorusunu cevaplar.
    """
    
    @staticmethod
    def run_simulation(symbol: str, target_date: str) -> Dict[str, Any]:
        """
        Belirtilen tarihe kadar olan veriyi alır (o gün dahil) ve ajanları toplantıya sokar.
        """
        md = MarketDataEngine()
        
        # Simülasyon için 5 yıllık geniş bir veri çekiyoruz ki geçmişte o tarihi kapsasın
        df_full = md.fetch_data(symbol, period="5y", interval="1d")
        
        if df_full.empty:
            return {"Error": "Veri çekilemedi."}
            
        try:
            # Datetime'a çevir ve o tarihe kadar olanı filtrele
            # timezone bilgisini kaldırarak karşılaştırma yapalım (yfinance tz-aware olabilir)
            df_full.index = df_full.index.tz_localize(None)
            cutoff_date = pd.to_datetime(target_date)
            
            df_sim = df_full[df_full.index <= cutoff_date]
            
            if df_sim.empty or len(df_sim) < 50:
                return {"Error": f"{target_date} tarihine kadar yeterli veri bulunamadı. Lütfen daha yakın bir tarih seçin."}
                
            # Ajanların kullanacağı contexti hazırla (SADECE simüle edilen veriye göre)
            tech = TechnicalEngine.calculate_all(df_sim)
            sm_res = SmartMoneyEngine.analyze_smart_money(df_sim)
            vol_res = VolumeAnalyticsEngine.analyze_volume(df_sim)
            ai_insight = SmartAI_Engine.generate_ai_insight(df_sim)
            
            context = {
                "tech": tech,
                "sm": sm_res,
                "vol": vol_res,
                "wyckoff": ai_insight.get("Wyckoff_Phase", "UNKNOWN"),
                "mani_risk": ai_insight.get("Manipulation_Analysis", {}).get("Risk_Score", 0)
            }
            
            # Ajanları toplantıya çağır
            coordinator = MultiAgentCoordinator()
            debate_res = coordinator.run_debate(df_sim, context)
            
            # Gelecekte (1 ay sonra) ne oldu? (Sadece raporlama için, ajanlar bunu bilmiyor)
            future_date = cutoff_date + datetime.timedelta(days=30)
            df_future = df_full[(df_full.index > cutoff_date) & (df_full.index <= future_date)]
            
            future_return_pct = 0
            if not df_future.empty:
                current_price = df_sim['Close'].iloc[-1]
                future_price = df_future['Close'].iloc[-1]
                future_return_pct = ((future_price - current_price) / current_price) * 100
                
            return {
                "Simulation_Date": target_date,
                "Current_Price": round(df_sim['Close'].iloc[-1], 2),
                "Debate_Result": debate_res,
                "Future_1M_Return": round(future_return_pct, 2) # Sadece gerçeği görmek için
            }
            
        except Exception as e:
            return {"Error": f"Simülasyon hatası: {str(e)}"}
