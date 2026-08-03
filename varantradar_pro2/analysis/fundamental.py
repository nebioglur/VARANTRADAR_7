from data.engines.fundamental_engine import FundamentalEngine as DataFundamentalEngine
from typing import Dict, Any, Union
from core.interfaces import BaseEngine

class FundamentalEngine(BaseEngine):
    """
    CFG-04 Analysis Architecture (Modül 76)
    Şirketin finansal tablolarını çeker, analiz eder ve BaseEngine
    kurallarına uygun olarak 0-100 arası skor döner.
    """
    
    def analyze(self, symbol: str, data: Any = None) -> Dict[str, Union[float, str]]:
        result = {
            "Score": 50.0,
            "Status": "UNKNOWN",
            "P_E_Ratio": "N/A",
            "P_B_Ratio": "N/A",
            "ROE": "N/A",
            "Debt_to_Equity": "N/A",
            "Profit_Margin": "N/A",
            "Sector": "N/A",
            "Industry": "N/A",
            "Analysis": "Veri çekilemedi."
        }
        
        try:
            data_engine = DataFundamentalEngine()
            ratios = data_engine.get_financial_ratios(symbol)
            
            pe = ratios.get("pe_ratio", "N/A")
            pb = ratios.get("pb_ratio", "N/A")
            roe = ratios.get("roe", "N/A")
            margin = ratios.get("profit_margin", "N/A")
            debt_eq = ratios.get("debt_to_equity", "N/A")
            
            result["Sector"] = ratios.get("sector", "N/A")
            result["Industry"] = ratios.get("industry", "N/A")
            
            score = 50.0
            
            if pe != "N/A" and isinstance(pe, (int, float)):
                result["P_E_Ratio"] = round(pe, 2)
                if 0 < pe <= 15: score += 15
                elif 15 < pe <= 25: score += 5
                elif pe > 30: score -= 15
                elif pe < 0: score -= 20 # Negatif PE (Zarar)
                
            if pb != "N/A" and isinstance(pb, (int, float)):
                result["P_B_Ratio"] = round(pb, 2)

            if margin != "N/A" and isinstance(margin, (int, float)):
                result["Profit_Margin"] = f"%{round(margin * 100, 2)}"
                
            if roe != "N/A" and isinstance(roe, (int, float)):
                result["ROE"] = f"%{round(roe * 100, 2)}"
                if roe >= 0.20: score += 20
                elif roe >= 0.10: score += 10
                elif roe < 0: score -= 20
                
            if debt_eq != "N/A" and isinstance(debt_eq, (int, float)):
                # debtToEquity is usually in percentage (e.g. 40 means 40% or 0.4 depending on provider. yfinance gives percentage like 150.5 for 1.5x)
                result["Debt_to_Equity"] = round(debt_eq, 2)
                if debt_eq < 50: score += 15
                elif debt_eq > 200: score -= 15
                elif debt_eq > 300: score -= 30
                
            score = max(0.0, min(100.0, float(score)))
            result["Score"] = score
            
            if score > 75:
                result["Status"] = "GÜÇLÜ"
                result["Analysis"] = "Şirketin finansalları (Value & Quality) güçlü."
            elif score > 45:
                result["Status"] = "NÖTR"
                result["Analysis"] = "Sektör ortalamasında."
            else:
                result["Status"] = "ZAYIF"
                result["Analysis"] = "Finansallar riskli (Z-Score alarmı)."
                
        except Exception as e:
            print(f"[FundamentalEngine] Hata: {e}")
            
        self.validate_output(result)
        return result
