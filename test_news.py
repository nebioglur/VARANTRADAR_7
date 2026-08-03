from gnews import GNews

google_news = GNews()
query = 'Türk Hava Yolları'
print(f"Fetching news for: {query}")
articles = google_news.get_news(query)

print(f"Found {len(articles)} articles.")
if len(articles) > 0:
    for a in articles[:3]:
        print("-", a.get('title'))
