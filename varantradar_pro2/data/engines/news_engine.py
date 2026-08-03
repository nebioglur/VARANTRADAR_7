from typing import List, Dict

import yfinance as yf

class NewsEngine:
    """
    CFG-03.2 — NEWS & SENTIMENT ENGINE
    
    KAP haberleri, Bloomberg/Reuters akışları ve sosyal duyarlılık analizi.
    """
    
    def __init__(self):
        pass
        
    def get_latest_news(self, symbol: str, limit: int = 5) -> List[Dict[str, str]]:
        """Şirket hakkındaki son haberleri döner. (Yahoo Finance üzerinden gerçek veriler)"""
        try:
            ticker = yf.Ticker(symbol)
            news_items = ticker.news
            
            formatted_news = []
            for n in news_items[:limit]:
                # yfinance news returns dicts with 'title', 'summary', 'link', 'providerPublishTime'
                formatted_news.append({
                    "title": n.get("title", ""),
                    "summary": n.get("summary", ""),
                    "link": n.get("link", ""),
                    "timestamp": n.get("providerPublishTime", 0)
                })
            return formatted_news
        except Exception:
            return []
        
    def get_sentiment_score(self, symbol: str) -> float:
        """Haber akışına göre duyarlılık skorunu SentimentEngine yapacak, bura sadece haber çeker."""
        return 50.0
