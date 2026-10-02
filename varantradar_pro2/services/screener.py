import concurrent.futures
import pandas as pd
from services.scraper import Scraper
from services.scoring import ScoringEngine
from utils.logger import logger

class MarketScreener:
    def __init__(self):
        self.scraper = Scraper()
        self.scorer = ScoringEngine()

    def scan_symbol(self, symbol: str) -> dict:
        """
        Fetches latest data for a single symbol and returns its score if it's a strong signal.
        """
        try:
            # First ensure we have the latest daily data to score
            self.scraper.fetch_data(symbol, period="6mo", interval="1d")
            
            # Generate score
            score_data = self.scorer.generate_score(symbol, interval="1d")
            
            return score_data
        except Exception as e:
            logger.error(f"Screener error for {symbol}: {str(e)}")
            return None

    def run_screener(self, symbols: list) -> pd.DataFrame:
        """
        Scans a list of symbols concurrently and returns the best opportunities.
        """
        logger.info(f"Starting Market Screener for {len(symbols)} symbols...")
        results = []
        
        # Use ThreadPoolExecutor to fetch and score concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {executor.submit(self.scan_symbol, sym): sym for sym in symbols}
            
            for future in concurrent.futures.as_completed(future_to_symbol):
                res = future.result()
                if res and res.get('action') in ["AL", "SAT"]:
                    results.append(res)
                    
        if not results:
            return pd.DataFrame()
            
        df = pd.DataFrame(results)
        # Sort by score descending for AL, ascending for SAT
        # Actually just sort by score descending so AL is at top, SAT at bottom
        df = df.sort_values(by="score", ascending=False)
        return df
