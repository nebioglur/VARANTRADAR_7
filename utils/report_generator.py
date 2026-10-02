import pandas as pd
from database.db_manager import DBManager
import os
from datetime import datetime

class ReportGenerator:
    """
    VarantRadar Pro V7 - Otomatik Rapor Merkezi
    İşlem geçmişini, portföy durumunu CSV ve Excel formatında dışa aktarır.
    """
    def __init__(self):
        self.db = DBManager()
        self.export_dir = "exports"
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)

    def generate_trade_journal_csv(self) -> str:
        """Kapanan işlemleri CSV olarak dışa aktarır."""
        conn = self.db.get_connection()
        try:
            df = pd.read_sql_query("SELECT * FROM trade_journal", conn)
            if df.empty:
                return None
                
            filename = f"{self.export_dir}/trade_journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False, encoding='utf-8')
            return filename
        finally:
            conn.close()

    def generate_portfolio_report_csv(self) -> str:
        """Portföy durumunu CSV olarak dışa aktarır."""
        conn = self.db.get_connection()
        try:
            df = pd.read_sql_query("SELECT * FROM portfolio", conn)
            if df.empty:
                return None
                
            filename = f"{self.export_dir}/portfolio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False, encoding='utf-8')
            return filename
        finally:
            conn.close()
