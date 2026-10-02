class GenerativeFeedbackEngine:
    """
    Simulates a Generative AI / NLP engine that analyzes multiple data points 
    (LSTM predictions, Technical Indicators, and Historical News Sentiment)
    to produce a human-readable, cohesive strategy report in Turkish.
    If a Gemini API key is configured, it will use real LLM.
    """
    def __init__(self):
        pass
        
    def generate_feedback(self, symbol, technicals, predictions, news_sentiment, confidence):
        """
        Generates a paragraph summarizing the AI's analysis.
        """
        # Parse inputs
        rsi = technicals.get('RSI_14', 50)
        ema20 = technicals.get('EMA_20', 0)
        ema50 = technicals.get('EMA_50', 0)
        
        # Determine trend
        trend = "yatay"
        if ema20 > ema50:
            trend = "yükseliş"
        elif ema20 < ema50:
            trend = "düşüş"
            
        # Analyze RSI
        rsi_status = "nötr bölgede"
        if rsi >= 70:
            rsi_status = "aşırı alım bölgesinde (düzeltme riski taşıyor)"
        elif rsi <= 30:
            rsi_status = "aşırı satım bölgesinde (tepki alımı gelebilir)"
            
        # Parse News
        news_desc = "nötr"
        if news_sentiment > 0.3:
            news_desc = "genel olarak pozitif (olumlu)"
        elif news_sentiment < -0.3:
            news_desc = "genel olarak negatif (olumsuz)"
            
        # AI Opinion
        if confidence >= 70:
            verdict = "Güçlü bir fırsat barındırıyor."
        elif confidence >= 50:
            verdict = "İzlenmeye değer bir potansiyel var, ancak risklere dikkat edilmeli."
        else:
            verdict = "Şu aşamada yeni bir pozisyon açmak için riskli görünüyor."
            
        fallback_summary = (
            f"VarantRadar Otonom Yapay Zeka Komitesi, {symbol} hissesini detaylı şekilde analiz etti. "
            f"Teknik olarak hisse {trend} trendinde hareket ediyor ve RSI göstergesi şu anda {rsi_status}. "
            f"Derin Öğrenme (LSTM) modelimizin geleceğe yönelik tahminleri %{confidence} güven skoru ile desteklenmektedir. "
            f"Ayrıca geriye dönük 6 aylık haber akışını incelediğimizde piyasa duyarlılığının {news_desc} olduğunu görüyoruz. "
            f"Sonuç olarak; sistemin ortak kararı: {verdict}"
        )
        
        try:
            from core.db_manager import DatabaseManager
            db = DatabaseManager()
            gemini_key = db.get_setting("gemini_api_key")
            
            if gemini_key and len(gemini_key) > 10:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                prompt = (
                    f"Sen usta bir Borsa İstanbul (BIST) analistisin. {symbol} hissesi için şu teknik veriler elimizde:\n"
                    f"Trend: {trend}\n"
                    f"RSI: {rsi_status}\n"
                    f"Genel Haber Duyarlılığı: {news_desc}\n"
                    f"Sistemimizin Güven Skoru: %{confidence} ({verdict})\n\n"
                    f"Bu verilere dayanarak, yatırımcılar için 3-4 cümlelik çok profesyonel, net ve yönlendirici bir teknik analiz sentezi (feedback) yazar mısın? "
                    f"Sadece analizi ver, selamlama veya kapanış kullanma."
                )
                
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
                    
        except Exception as e:
            print(f"Gemini API Hatası: {e}")
            
        return fallback_summary
