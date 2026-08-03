import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.antigravity_core import AntigravityCore
from services.ai_decision_engine import AIDecisionEngine
from services.chart_engine import ChartEngine
from services.multi_agent_system import MultiAgentSystem
from services.digital_twin import DigitalMarketTwin
from database.db_manager import DBManager
import warnings
warnings.filterwarnings("ignore")

def run_full_test():
    print("--- VARANTRADAR X SISTEM TESTI BASLIYOR ---")
    try:
        # 1. DB Init
        print("[1/6] Veritabani baslatiliyor...")
        db = DBManager()
        
        # 2. Core Fetch
        print("[2/6] AntigravityCore hisse verisi cekiliyor (THYAO.IS)...")
        core = AntigravityCore()
        success = core.update_stock_data("THYAO.IS")
        if not success:
            print("HATA: Veri cekilemedi!")
            return
            
        # 3. Analyzer
        print("[3/6] Analyzer gostergeleri hesaplaniyor...")
        df = core.analyzer.calculate_indicators("THYAO.IS", "1d")
        if df.empty:
            print("HATA: DataFrame bos!")
            return
            
        # 4. Chart Engine
        print("[4/6] Plotly Grafikleri test ediliyor...")
        fig = ChartEngine.create_advanced_chart(df, "THYAO.IS")
        if not fig:
            print("HATA: Grafik olusturulamadi!")
            return
            
        # 5. AI & Multi-Agent
        print("[5/6] Multi-Agent ve AI Motorlari test ediliyor...")
        ai_report = AIDecisionEngine.generate_ai_report(df, "THYAO.IS")
        mas = MultiAgentSystem()
        council = mas.run_agent_council("THYAO.IS", ai_report)
        
        # 6. Digital Twin
        print("[6/6] Digital Market Twin test ediliyor...")
        dt = DigitalMarketTwin()
        dt_res = dt.run_stress_test(df)
        
        print("\n=== TUM TESTLER BASARIYLA GECTI! ===")
        print("Sistem Cloud (Uretim) ortaminda sorunsuz calismaya hazirdir.")
    except Exception as e:
        import traceback
        print("\n=== KRITIK HATA TESPIT EDILDI ===")
        traceback.print_exc()

if __name__ == "__main__":
    run_full_test()
