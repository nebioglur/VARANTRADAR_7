import yfinance as yf
from typing import Dict, Any

class FundamentalEngine:
    """
    Enterprise Quant & Fundamental Intelligence (Modül 76).
    Şirketin finansal tablolarını (Bilanço, P/E, Oranlar) çeker ve analiz eder.
    Hata töleranslıdır (Fault Tolerant); veri çekilemezse sistemi çökertmez.
    """
    
    @staticmethod
    def analyze_fundamentals(symbol: str) -> Dict[str, Any]:
        """
        Belirtilen hisse senedi için Temel Analiz verilerini çeker ve
        Kantitatif bir sağlık skoru (Piotroski simülasyonu) oluşturur.
        """
        result = {
            "Status": "UNKNOWN",
            "P_E_Ratio": "N/A",
            "P_B_Ratio": "N/A",
            "ROE": "N/A",
            "Debt_to_Equity": "N/A",
            "Profit_Margin": "N/A",
            "Fundamental_Score": 50, # 0-100 arası (Default 50)
            "Piotroski_Estimate": "N/A",
            "Analysis": "Veri çekilemedi. Teknik ve Quant modellere ağırlık verilmeli."
        }
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info or "trailingPE" not in info:
                return result # YFinance bazı BIST hisselerinde info dönemeyebilir
                
            # Oranları çek
            pe = info.get("trailingPE", "N/A")
            pb = info.get("priceToBook", "N/A")
            roe = info.get("returnOnEquity", "N/A")
            debt_eq = info.get("debtToEquity", "N/A")
            margin = info.get("profitMargins", "N/A")
            
            # Verileri normalize et ve formatla
            if pe != "N/A": result["P_E_Ratio"] = round(pe, 2)
            if pb != "N/A": result["P_B_Ratio"] = round(pb, 2)
            if roe != "N/A": result["ROE"] = f"%{round(roe * 100, 2)}"
            if debt_eq != "N/A": result["Debt_to_Equity"] = round(debt_eq, 2)
            if margin != "N/A": result["Profit_Margin"] = f"%{round(margin * 100, 2)}"
            
            # Basit bir Kantitatif Skorlama (Piotroski-Benzeri Kalite Skoru Simülasyonu)
            score = 50
            if pe != "N/A" and pe < 15 and pe > 0: score += 10 # Ucuz Çarpan (Value Factor)
            if pe != "N/A" and pe > 30: score -= 10 # Çok Pahalı
            
            if roe != "N/A" and roe > 0.15: score += 15 # Yüksek Karlılık (Quality Factor)
            if roe != "N/A" and roe < 0: score -= 15 # Zarar
            
            if debt_eq != "N/A" and debt_eq < 100: score += 10 # Düşük Borç (Risk Factor)
            if debt_eq != "N/A" and debt_eq > 250: score -= 10 # Yüksek Borç Riski
            
            if margin != "N/A" and margin > 0.10: score += 10 # İyi Kar Marjı
            
            score = max(0, min(100, score)) # 0-100 aralığına hapset
            
            result["Fundamental_Score"] = score
            
            # Yorumlama
            if score > 75:
                result["Status"] = "GÜÇLÜ (STRONG)"
                result["Piotroski_Estimate"] = "7-9 (Yüksek Kalite)"
                result["Analysis"] = "Şirketin finansalları ve temel rasyoları (Quant Faktörleri) çok güçlü. Uzun vadeli yatırıma (Value & Quality) uygun."
            elif score > 45:
                result["Status"] = "NÖTR (NEUTRAL)"
                result["Piotroski_Estimate"] = "4-6 (Ortalama)"
                result["Analysis"] = "Finansallar sektör ortalamasında. Ciddi bir iflas riski yok ancak büyüme tarafında mucize beklenmiyor."
            else:
                result["Status"] = "ZAYIF (WEAK / DISTRESS)"
                result["Piotroski_Estimate"] = "0-3 (Riskli Bölge)"
                result["Analysis"] = "Finansallar Alarm veriyor (Altman Z-Score risk bölgesi). Borçlar yüksek veya şirket kâr edemiyor."
                
            return result
            
        except Exception as e:
            # Hata durumunda sistemi çökertme
            return result
