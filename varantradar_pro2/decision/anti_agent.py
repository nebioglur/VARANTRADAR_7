from typing import Dict, Any

class AntiAgent:
    """
    CFG-05 Decision Architecture (Counter Opinion - Şeytanın Avukatı)
    Executive Engine'in verdiği alım kararına kasten itiraz eder.
    En zayıf halkanın (En düşük motor skoru) riskini büyütüp masaya koyar.
    """
    
    @staticmethod
    def challenge_decision(engine_scores: Dict[str, float], base_confidence: float) -> Dict[str, Any]:
        """
        Girdi: 5 motorun skoru ve temel güven skoru.
        Çıktı: İtiraz metni ve yeni (muhtemelen düşürülmüş) güven skoru.
        """
        result = {
            "Counter_Opinion": "Sistemde belirgin bir zayıflık tespit edilemedi.",
            "Penalty": 0.0,
            "Adjusted_Confidence": base_confidence
        }
        
        # En düşük skoru bul
        if not engine_scores:
            return result
            
        weakest_engine = min(engine_scores, key=engine_scores.get)
        weakest_score = engine_scores[weakest_engine]
        
        penalty = 0.0
        opinion = ""
        
        # Sadece zayıf puanlara itiraz et (< 45)
        if weakest_score < 45:
            if weakest_engine == "Fundamental":
                opinion = "DİKKAT (Şeytanın Avukatı): Teknik göstergeler cazip olsa da, şirketin Temel Analiz skoru alarm veriyor. Kötü bir bilanço veya iflas riski, teknik trendi aniden çökertebilir."
                penalty = 10.0
            elif weakest_engine == "SmartMoney":
                opinion = "DİKKAT (Şeytanın Avukatı): Trend yükselişte görünse bile, Kurumsal Hacim (Smart Money) hisseyi desteklemiyor. Bu yükseliş perakende yatırımcı tarafından tetiklenen bir 'BULL TRAP (Boğa Tuzağı)' olabilir."
                penalty = 15.0 # Smart money uyumsuzluğu kritiktir
            elif weakest_engine == "Macro":
                opinion = "DİKKAT (Şeytanın Avukatı): Bu hissenin kendi grafiği iyi olsa dahi, genel Piyasa Rejimi (Macro) negatif veya aşırı volatil. Fırtınalı bir havada en sağlam gemi bile batabilir."
                penalty = 12.0
            elif weakest_engine == "Sentiment":
                opinion = "DİKKAT (Şeytanın Avukatı): Haber akışı veya piyasa algısı oldukça negatif. Yaklaşan bir dava veya kriz, grafikteki tüm destekleri kırabilir."
                penalty = 8.0
            elif weakest_engine == "Technical":
                opinion = "DİKKAT (Şeytanın Avukatı): Temel veriler ve hacim iyi olsa da, henüz teknik bir 'Trend Dönüşü' yok. Erken giriş (Düşen bıçağı tutmak) riski var."
                penalty = 5.0
                
        # Güven skorunu cezalandır
        new_confidence = max(0.0, base_confidence - penalty)
        
        result["Counter_Opinion"] = opinion if opinion else "Mükemmel kurulum: Motorların hiçbiri kritik bir zayıflık göstermiyor."
        result["Penalty"] = penalty
        result["Adjusted_Confidence"] = round(new_confidence, 2)
        
        return result
