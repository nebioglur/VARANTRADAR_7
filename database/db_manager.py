import sqlite3
import pandas as pd
import os
import shutil
from datetime import datetime
from config.settings import DB_PATH
from utils.logger import logger
from utils.exceptions import DatabaseError

class DBManager:
    def __init__(self):
        self.db_path = DB_PATH
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        # Cloud (Streamlit) ortamında DB sıfırlanırsa tabloları otomatik kurması için eklendi (V12 Fix)
        from database.models import create_tables
        create_tables()
        
    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def backup_database(self):
        """Veritabanını yedekler (Modül 3.10)"""
        try:
            backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"varantradar_backup_{timestamp}.db")
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up successfully to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return False

    def insert_stock_data(self, df: pd.DataFrame, symbol: str, interval: str = "1d"):
        try:
            conn = self.get_connection()
            # Lowercase columns for safety
            df.columns = [c.lower() for c in df.columns]
            for index, row in df.iterrows():
                conn.execute('''
                    REPLACE INTO stock_data (symbol, date, interval, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (symbol, str(index), interval, row['open'], row['high'], row['low'], row['close'], row['volume']))
            conn.commit()
            conn.close()
        except Exception as e:
            raise DatabaseError(f"Error inserting stock data for {symbol}: {e}")

    def get_stock_data(self, symbol: str, interval: str = "1d") -> pd.DataFrame:
        try:
            conn = self.get_connection()
            query = f"SELECT * FROM stock_data WHERE symbol = '{symbol}' AND interval = '{interval}' ORDER BY date ASC"
            df = pd.read_sql_query(query, conn)
            conn.close()
            if not df.empty:
                # Convert 'date' string back to datetime index for analysis (En Güvenilir Çözüm - Timezone hatasını engeller)
                df['date'] = df['date'].astype(str).str.replace(r'\+.*', '', regex=True).apply(lambda x: pd.to_datetime(x, errors='coerce'))
                df.dropna(subset=['date'], inplace=True)
                df.set_index('date', inplace=True)
            return df
        except Exception as e:
            raise DatabaseError(f"Error reading stock data for {symbol}: {e}")

    def add_to_watchlist(self, symbol: str, is_favorite: bool = False):
        try:
            conn = self.get_connection()
            conn.execute('''
                REPLACE INTO watchlist (symbol, is_favorite, added_at)
                VALUES (?, ?, ?)
            ''', (symbol, is_favorite, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")

    def get_setting(self, key: str, default: str = None) -> str:
        """Belirtilen ayar anahtarının değerini getirir."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT setting_value FROM settings WHERE setting_key = ?", (key,))
            row = cursor.fetchone()
            conn.close()
            return row[0] if row and row[0] is not None else default
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default

    def save_setting(self, key: str, value: str) -> bool:
        """Belirtilen ayar anahtarını kaydeder veya günceller."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO settings (setting_key, setting_value, updated_at) 
                VALUES (?, ?, ?)
                ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value, updated_at = excluded.updated_at
            """, (key, value, now))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving setting {key}: {e}")
            return False
