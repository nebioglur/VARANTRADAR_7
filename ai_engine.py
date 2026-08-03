from utils.logger import logger

class AIEngine:
    def __init__(self):
        # In a real app, this would initialize an LLM client (e.g. Gemini, OpenAI)
        self.model_name = "Mock-AI-Model"

    def generate_stock_analysis(self, symbol: str, score_data: dict) -> str:
        """
        Generates a natural language summary explaining the technical setup.
        """
        score = score_data.get("score", 50)
        action = score_data.get("action", "BEKLE")
        reasons = score_data.get("reasoning", "")
        
        logger.info(f"Generating AI analysis for {symbol}...")
        
        if action == "AL":
            analysis = f"Yapay Zeka Yorumu: {symbol} için teknik göstergeler oldukça pozitif bir tablo çiziyor. " \
                       f"Hacim destekli yükseliş ve momentum, alıcıların güçlü olduğuna işaret ediyor. " \
                       f"Güven puanı {score}/100. Destek noktalarından dönüşler ve indikatör onayları mevcut.\n\n" \
                       f"Detaylar:\n{reasons}"
        elif action == "SAT":
            analysis = f"Yapay Zeka Yorumu: {symbol} cephesinde riskler artmış durumda. " \
                       f"Teknik göstergelerde aşırı alım bölgesi yorgunluklarına ve olası dönüşlere dikkat edilmeli. " \
                       f"Güven puanı sadece {score}/100. Pozisyonların küçültülmesi veya stop-loss seviyelerinin yakına çekilmesi önerilir.\n\n" \
                       f"Detaylar:\n{reasons}"
        else:
            analysis = f"Yapay Zeka Yorumu: {symbol} için piyasa şu an kararsız bir bölgede. " \
                       f"Yeni bir pozisyon açmak için teknik kırılımlar veya daha net hacim girişleri beklenmeli. " \
                       f"Güven puanı nötr ({score}/100).\n\n" \
                       f"Detaylar:\n{reasons}"
                       
        return analysis

    def risk_analysis(self, volatility: float, drawdown: float) -> str:
        if volatility > 40 or drawdown > 20:
            return "Risk Seviyesi: YÜKSEK - Bu varlıkta sert fiyat hareketleri görülmektedir."
        elif volatility > 20 or drawdown > 10:
            return "Risk Seviyesi: ORTA - Dengeli bir risk/getiri profiline sahiptir."
        else:
            return "Risk Seviyesi: DÜŞÜK - Göreceli olarak istikrarlı fiyatlanmaktadır."

ai_engine = AIEngine()
