from data.engines.news_engine import NewsEngine as DataNewsEngine
from typing import Dict, Any, Union
from core.interfaces import BaseEngine
from core.event_bus import EventBus

class SentimentEngine(BaseEngine):
    """
    CFG-04 Analysis Architecture (Sentiment Engine)
    Hisse haberlerini çeker, NLP analizi yapar ve BaseEngine
    kurallarına uygun olarak 0-100 arası skor döner.
    """
    
    POSITIVE_WORDS = ['büyüme', 'kâr', 'anlaşma', 'temettü', 'rekor', 'yükseliş', 'yatırım', 'satın alma', 'up', 'growth', 'profit', 'dividend', 'record', 'buy', 'upgrade', 'beat', 'higher', 'surge', 'jump', 'gain', 'revenue', 'strong', 'positive', 'bullish']
    NEGATIVE_WORDS = ['zarar', 'düşüş', 'kriz', 'istifa', 'ceza', 'dava', 'iflas', 'uyarı', 'down', 'loss', 'decline', 'penalty', 'lawsuit', 'bankruptcy', 'downgrade', 'miss', 'lower', 'debt', 'weak', 'negative', 'bearish', 'drop', 'fall', 'plunge', 'sell', 'warning']
    
    def analyze(self, symbol: str, data: Any = None) -> Dict[str, Union[float, str]]:
        result = {
            "Score": 50.0,
            "Status": "UNKNOWN",
            "News_Count": 0,
            "Analysis": "Yeterli haber bulunamadı."
        }
        
        try:
            news_engine = DataNewsEngine()
            news = news_engine.get_latest_news(symbol, limit=8)
            
            if not news:
                self.validate_output(result)
                return result
                
            headlines = []
            total_sentiment = 0.0
            
            for item in news:
                title = item.get("title", "")
                summary = item.get("summary", "")
                content_lower = (title + " " + summary).lower()
                
                pos_count = sum(1 for word in self.POSITIVE_WORDS if word in content_lower)
                neg_count = sum(1 for word in self.NEGATIVE_WORDS if word in content_lower)
                
                # Base score is 50. Each positive word adds 15, negative subtracts 15.
                item_score = 50.0 + (pos_count * 15.0) - (neg_count * 15.0)
                item_score = max(0.0, min(100.0, float(item_score)))
                
                total_sentiment += item_score
                headlines.append(title)
                
            avg_sentiment = total_sentiment / len(headlines) if headlines else 50.0
            
            result["News_Count"] = len(headlines)
            result["Score"] = round(avg_sentiment, 2)
            
            if avg_sentiment >= 65:
                result["Status"] = "POZİTİF"
                result["Analysis"] = "Haber akışı ve piyasa algısı olumlu."
            elif avg_sentiment <= 35:
                result["Status"] = "NEGATİF"
                result["Analysis"] = "Haber akışında ciddi negatiflik var."
                
                EventBus.publish("CRITICAL_NEWS_ALERT", {
                    "symbol": symbol,
                    "score": avg_sentiment,
                    "msg": "Negatif haber akışı tespit edildi!"
                })
            else:
                result["Status"] = "NÖTR"
                result["Analysis"] = "Haber akışı standart seyrinde."
                
        except Exception as e:
            print(f"[SentimentEngine] Hata: {e}")
            
        self.validate_output(result)
        return result
