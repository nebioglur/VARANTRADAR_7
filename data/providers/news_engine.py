import traceback
from gnews import GNews
from textblob import TextBlob
from datetime import datetime, timedelta

class NewsEngine:
    """
    Fetches historical news for a given stock symbol using Google News (via gnews).
    Performs basic sentiment analysis using TextBlob.
    """
    def __init__(self):
        # Set up GNews for Turkey / Turkish
        self.google_news = GNews(language='tr', country='TR', period='6m', max_results=30)
        
    def fetch_news(self, symbol):
        """
        Fetches up to 30 news articles from the past 6 months for the given symbol.
        """
        try:
            # Clean symbol (e.g. remove .IS)
            clean_symbol = symbol.replace('.IS', '')
            
            # Form query
            query = f'"{clean_symbol}" hisse OR borsa'
            
            # Fetch
            articles = self.google_news.get_news(query)
            
            if not articles:
                return []
                
            formatted_news = []
            for article in articles:
                title = article.get('title', '')
                desc = article.get('description', '')
                published = article.get('published date', '')
                url = article.get('url', '')
                publisher = article.get('publisher', {}).get('title', 'Haber')
                
                # Basic sentiment on title
                sentiment = self._analyze_sentiment(title)
                
                formatted_news.append({
                    "title": title,
                    "description": desc,
                    "published": published,
                    "url": url,
                    "publisher": publisher,
                    "sentiment": sentiment
                })
                
            # Sort by date (newest first)
            # gnews returns date as 'Thu, 20 Jul 2023 07:00:00 GMT'
            # We'll just rely on the API's sorting or do a basic sort if needed.
            return formatted_news
            
        except Exception as e:
            print(f"[NewsEngine] Error fetching news for {symbol}: {e}")
            traceback.print_exc()
            return []
            
    def _analyze_sentiment(self, text):
        """
        Returns basic sentiment (-1.0 to 1.0). 
        Note: TextBlob works best in English, but it can work for basic polarity or we translate.
        For V2, we will use TextBlob's basic translation or keep it simple.
        Since it's Turkish, TextBlob might not be accurate without translation. 
        As a lightweight approach, we'll try to use a heuristic keyword match if translation fails.
        """
        positive_keywords = ['arttı', 'yükseldi', 'kâr', 'büyüme', 'pozitif', 'rekor', 'temettü', 'anlaşma', 'kazanç']
        negative_keywords = ['düştü', 'zarar', 'geriledi', 'negatif', 'düşüş', 'kayıp', 'ceza', 'kriz']
        
        text_lower = text.lower()
        score = 0.0
        
        for word in positive_keywords:
            if word in text_lower:
                score += 0.5
                
        for word in negative_keywords:
            if word in text_lower:
                score -= 0.5
                
        # Cap between -1 and 1
        return max(-1.0, min(1.0, score))
