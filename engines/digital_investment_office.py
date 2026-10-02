from typing import Dict, Any
from engines.executive_decision_engine import ExecutiveDecisionEngine

class DigitalInvestmentOffice:
    """
    Modül 99: Digital Investment Office (Sanal Yönetim Kurulu).
    Sistemdeki "Executive Decision Engine" verilerini alır ve 
    AI Yöneticileri (CIO, CRO, Quant Director, Economist) karakterlerine bürünerek 
    Kullanıcıya (Board) bir yönetim kurulu toplantısı (Brifing) sunar.
    """
    
    @staticmethod
    def hold_board_meeting(symbol: str, macro_symbol: str = "XU100.IS") -> Dict[str, Any]:
        """Sanal Yönetim Kurulu Toplantısını başlatır."""
        
        # 1. Merkezden tüm analizlerin özetini al
        exec_data = ExecutiveDecisionEngine.generate_executive_decision(symbol, macro_symbol)
        scores = exec_data["Scores"]
        
        # 2. Sanal Yöneticilerin Yorumları (Persona based generation)
        
        # AI Chief Investment Officer (CIO) - Nihai Karar Verici
        cio_opinion = f"Sayın Yönetim Kurulu, {symbol} için genel Güven Skorumuz %{exec_data['Confidence_Score']}. Kararım: **{exec_data['Final_Decision']}**. {exec_data['Executive_Summary']}"
        
        # AI Chief Risk Officer (CRO) - Risk ve Sentiment odaklı
        cro_opinion = "Riskler kontrol altında."
        if scores['Sentiment']['Score'] < 40 or scores['Macro_Regime']['Status'] == "AYI (BEAR)":
            cro_opinion = f"Dikkatli olmalıyız. Makro rejim {scores['Macro_Regime']['Status']} yönünde ve haber akışı zayıf (Skor: {scores['Sentiment']['Score']}). Sermayeyi koruma moduna geçmeliyiz."
        elif scores['Sentiment']['Score'] > 70:
            cro_opinion = "Piyasa duyarlılığı pozitif ancak her zaman bir Stop-Loss seviyesi belirleyerek işlem yapmalıyız."
            
        # AI Quant Director - Fundamental ve Teknik Verilere Odaklı
        quant_opinion = f"Kantitatif modellere göre: Teknik Skorumuz {scores['Technical']['Score']}/100, Bilanço/Kalite Skorumuz ise {scores['Fundamental']['Score']}/100. "
        if scores['Technical']['Score'] > 60 and scores['Fundamental']['Score'] > 60:
            quant_opinion += "Hem teknik ivme hem de şirket temelleri (Value/Quality) güçlü bir sinerji oluşturuyor."
        else:
            quant_opinion += "Verilerde bir uyumsuzluk var (Divergence). Fiyat artarken bilançolar desteklemiyor veya tam tersi olabilir."
            
        # AI Chief Economist - Makro Çerçeve
        eco_opinion = f"{macro_symbol} endeksini baz aldığımızda, genel piyasa rejimi {scores['Macro_Regime']['Status']} olarak hesaplanmıştır. Küresel likidite ve iç pazar dinamiklerini dikkate alarak pozisyon büyüklüğünüzü ayarlayın."
        
        return {
            "Symbol": symbol,
            "Executive_Data": exec_data,
            "Meeting_Minutes": {
                "AI_CIO": cio_opinion,
                "AI_CRO": cro_opinion,
                "AI_Quant_Director": quant_opinion,
                "AI_Economist": eco_opinion
            }
        }
