import yfinance as yf
from typing import Dict, Any, List
from core.event_bus import EventBus

class SentimentEngine:
    """
    Hisse özelindeki haberleri çeker ve basit bir NLP (Kelime bazlı) Sentiment analizi yapar.
    Eğer çok negatif haber varsa (Kriz) FinOS Event Bus üzerinden acil durum alarmı fırlatır.
    """
    
    # Basit sentiment sözlükleri (Gerçekte LLM veya hazır NLP modeli kullanılır)
    POSITIVE_WORDS = ['büyüme', 'kâr', 'anlaşma', 'temettü', 'rekor', 'yükseliş', 'yatırım', 'satın alma', 'up', 'growth', 'profit', 'dividend', 'record', 'buy', 'upgrade', 'beat', 'higher']
    NEGATIVE_WORDS = ['zarar', 'düşüş', 'kriz', 'istifa', 'ceza', 'dava', 'iflas', 'uyarı', 'down', 'loss', 'decline', 'penalty', 'lawsuit', 'bankruptcy', 'downgrade', 'miss', 'lower', 'debt']
    
    @staticmethod
    def analyze_news(symbol: str) -> Dict[str, Any]:
        result = {
            "Status": "UNKNOWN",
            "Sentiment_Score": 50, # 0-100 (0: Extreme Fear, 100: Extreme Greed)
            "News_Count": 0,
            "Headlines": [],
            "Analysis": "Yeterli haber bulunamadı."
        }
        
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            if not news:
                return result
                
            headlines = []
            total_sentiment = 0
            
            for item in news[:5]: # Son 5 haber
                title = item.get("title", "")
                link = item.get("link", "")
                
                # Başlığı küçük harfe çevirip basit analiz yap
                title_lower = title.lower()
                
                pos_count = sum(1 for word in SentimentEngine.POSITIVE_WORDS if word in title_lower)
                neg_count = sum(1 for word in SentimentEngine.NEGATIVE_WORDS if word in title_lower)
                
                item_score = 50 + (pos_count * 15) - (neg_count * 15)
                item_score = max(0, min(100, item_score))
                
                total_sentiment += item_score
                
                headlines.append({
                    "title": title,
                    "link": link,
                    "sentiment": item_score
                })
                
            avg_sentiment = total_sentiment / len(headlines)
            
            result["News_Count"] = len(headlines)
            result["Headlines"] = headlines
            result["Sentiment_Score"] = round(avg_sentiment, 2)
            
            # Yorumlama
            if avg_sentiment >= 65:
                result["Status"] = "POZİTİF (BULLISH)"
                result["Analysis"] = "Haber akışı ve piyasa algısı şirket için oldukça olumlu."
            elif avg_sentiment <= 35:
                result["Status"] = "NEGATİF (BEARISH)"
                result["Analysis"] = "Haber akışında ciddi negatiflik var. Yatırımcı güveni sarsılmış olabilir."
                
                # FinOS Event Bus'a KRİTİK HABER alarmı gönder
                eb = EventBus()
                eb.publish("CRITICAL_NEWS_ALERT", {"symbol": symbol, "score": avg_sentiment, "msg": "Negatif haber akışı tespit edildi!"})
            else:
                result["Status"] = "NÖTR (NEUTRAL)"
                result["Analysis"] = "Haber akışı standart seyrinde. Piyasayı sarsacak bir durum yok."
                
            return result
            
        except Exception as e:
            result["Analysis"] = f"Haberler çekilirken hata oluştu: {str(e)}"
            return result
