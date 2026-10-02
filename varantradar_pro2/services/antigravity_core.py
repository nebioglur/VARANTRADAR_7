from services.scraper import Scraper
from services.analyzer import Analyzer
from database.models import create_tables
from utils.logger import logger

class AntigravityCore:
    def __init__(self):
        self.scraper = Scraper()
        self.analyzer = Analyzer()
        
    def initialize_system(self):
        logger.info("Initializing Antigravity Core...")
        create_tables()
        logger.info("Database tables created.")
        
    def update_all_data(self):
        logger.info("Starting data update cycle...")
        self.scraper.run_all()
        logger.info("Data update complete.")

    def update_stock_data(self, symbol: str):
        try:
            logger.info(f"Starting data update cycle for single symbol: {symbol}")
            self.scraper.fetch_all_intervals_for_symbol(symbol)
            logger.info(f"Data update complete for {symbol}.")
            return True
        except Exception as e:
            logger.error(f"Error during data update for {symbol}: {str(e)}")
            return False
        
    def analyze_stock(self, symbol: str):
        df = self.analyzer.calculate_indicators(symbol)
        if not df.empty:
            logger.info(f"Analysis complete for {symbol}. Latest RSI: {df['RSI'].iloc[-1]:.2f}")
        return df

if __name__ == "__main__":
    core = AntigravityCore()
    core.initialize_system()
    core.update_all_data()
    core.analyze_stock("ASELS.IS")
