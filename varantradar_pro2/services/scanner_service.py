from engines.radar_engine import RadarEngine
from database.db_manager import DBManager
import pandas as pd
from config.bist_symbols import BIST30_SYMBOLS

class ScannerService:
    def __init__(self):
        self.radar = RadarEngine()
        self.db = DBManager()

    @property
    def is_scanning(self):
        return self.radar.is_scanning

    def start_background_scan(self, symbols=BIST30_SYMBOLS, interval="1d"):
        return self.radar.start_background_scan(symbols)

    def get_latest_results(self):
        conn = self.db.get_connection()
        df = pd.read_sql_query("SELECT * FROM scan_results ORDER BY total_score DESC", conn)
        conn.close()
        return df
