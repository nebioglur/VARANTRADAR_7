import pandas as pd
from database.db_manager import DBManager
from utils.logger import logger

class HistoryEngine:
    """
    Geçmiş işlemleri, sistemin başarı oranını (Hit Rate) ve sinyal kalitesini ölçmekle görevli motordur.
    Sistemin kendi kendine öğrenme ve performans takip (CFG-04) modülünün temelidir.
    """
    
    def __init__(self):
        self.db = DBManager()

    def get_signal_hit_rate(self) -> float:
        """
        Sistemin kapalı (başarılı veya başarısız) sinyallerinin oranını hesaplar.
        """
        conn = self.db.get_connection()
        try:
            # Sadece kapalı olanları (başarılı/başarısız) alıyoruz.
            df = pd.read_sql_query("SELECT * FROM signals_history WHERE status IN ('PROFIT', 'LOSS')", conn)
            if df.empty:
                return 0.0
                
            successful_trades = len(df[df['status'] == 'PROFIT'])
            total_closed_trades = len(df)
            
            hit_rate = (successful_trades / total_closed_trades) * 100
            return round(hit_rate, 2)
        except Exception as e:
            logger.error(f"[HistoryEngine] Hit Rate hesaplama hatası: {e}")
            return 0.0
        finally:
            conn.close()

    def update_pending_signals(self, current_market_data: pd.DataFrame):
        """
        Şu anki piyasa verilerine bakarak 'PENDING' olan eski sinyallerin hedefe veya stopa
        ulaşıp ulaşmadığını kontrol eder.
        """
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, symbol, entry_price, target_price, stop_loss, trade_type FROM signals_history WHERE status='PENDING'")
            pending_signals = cursor.fetchall()
            
            for sig_id, symbol, entry, target, stop, trade_type in pending_signals:
                if symbol not in current_market_data['symbol'].values:
                    continue
                    
                current_price = current_market_data[current_market_data['symbol'] == symbol]['close'].iloc[-1]
                
                is_long = "AL" in trade_type.upper() or "SWING" in trade_type.upper()
                
                if is_long:
                    if current_price >= target:
                        cursor.execute("UPDATE signals_history SET status='PROFIT', exit_price=?, exit_date=CURRENT_TIMESTAMP WHERE id=?", (current_price, sig_id))
                    elif current_price <= stop:
                        cursor.execute("UPDATE signals_history SET status='LOSS', exit_price=?, exit_date=CURRENT_TIMESTAMP WHERE id=?", (current_price, sig_id))
                else: # SHORT scenario
                    if current_price <= target:
                        cursor.execute("UPDATE signals_history SET status='PROFIT', exit_price=?, exit_date=CURRENT_TIMESTAMP WHERE id=?", (current_price, sig_id))
                    elif current_price >= stop:
                        cursor.execute("UPDATE signals_history SET status='LOSS', exit_price=?, exit_date=CURRENT_TIMESTAMP WHERE id=?", (current_price, sig_id))
                        
            conn.commit()
        except Exception as e:
            logger.error(f"[HistoryEngine] Pending signals güncelleme hatası: {e}")
        finally:
            conn.close()

    def get_latest_signals(self, limit: int = 10) -> pd.DataFrame:
        """
        Dashboard'da göstermek üzere son sinyalleri getirir.
        """
        conn = self.db.get_connection()
        try:
            df = pd.read_sql_query(f"SELECT * FROM signals_history ORDER BY signal_date DESC LIMIT {limit}", conn)
            return df
        finally:
            conn.close()
