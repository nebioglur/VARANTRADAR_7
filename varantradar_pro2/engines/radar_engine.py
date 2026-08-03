import concurrent.futures
import threading
from datetime import datetime
from typing import List, Dict, Any

from utils.logger import logger
from database.db_manager import DBManager
from engines.market_data_engine import MarketDataEngine
from services.analyzer import Analyzer
from services.matcher import WarrantMatcher

class RadarEngine:
    """
    Tüm varlıkları paralel olarak taramak ve radar kuyruğunu yönetmekten sorumludur.
    (Single Responsibility: Orchestrating the scan loop)
    """
    
    def __init__(self):
        self.market_data = MarketDataEngine()
        self.analyzer = Analyzer()
        self.matcher = WarrantMatcher()
        self.db = DBManager()
        self.is_scanning = False

    def scan_single_symbol(self, sym: str) -> Dict[str, Any]:
        """Tek bir hisseyi tarar ve AI raporunu döner."""
        try:
            # 1. Veri Çekme (Market Data Engine)
            df_1d = self.market_data.fetch_data(sym, interval="1d")
            df_4h = self.market_data.fetch_data(sym, interval="4h")
            
            if df_1d.empty:
                return None
                
            # DB kayıt işlemleri (Opsiyonel olarak ayrı bir servise alınabilir)
            self.db.insert_stock_data(df_1d, sym, "1d")
            if not df_4h.empty:
                self.db.insert_stock_data(df_4h, sym, "4h")
            
            # 2. Teknik Analiz (Şimdilik eski Analyzer'ı kullanıyoruz, yakında teknik motorlar devralacak)
            df_1d = self.analyzer.calculate_indicators_on_df(df_1d)
            df_4h = self.analyzer.calculate_indicators_on_df(df_4h) if not df_4h.empty else pd.DataFrame()
            
            if df_1d.empty:
                return None
                
            # 3. AI Kararı (DI ile çalışan güncel AI Decision Engine)
            from services.ai_decision_engine import AIDecisionEngine
            ai_report = AIDecisionEngine.generate_ai_report(df_1d, sym, df_4h)
            
            if "error" in ai_report:
                return None
                
            # 4. Varant Eşleştirme (CFG-03 Asset agnostic olduğu için sadece uygunsa yapılır)
            best_warrant = ""
            if ai_report['Trade_Type'] != "Bekle / Yatay Piyasada İşlem Yapma":
                is_call = "AL" in ai_report['Trade_Type'].upper() or "SWING" in ai_report['Trade_Type'].upper()
                warrants = self.matcher.find_best_warrants(sym, is_call)
                if not warrants.empty:
                    best_warrant = warrants.iloc[0]['warrant_code']
                    
            return {
                "sym": sym,
                "ai_report": ai_report,
                "best_warrant": best_warrant,
                "df_1d_last": df_1d.iloc[-1]
            }
        except Exception as e:
            logger.error(f"[RadarEngine] Error scanning {sym}: {e}")
            return None

    def start_background_scan(self, symbols: List[str]) -> bool:
        if self.is_scanning:
            return False
            
        def scan_task():
            self.is_scanning = True
            logger.info(f"[RadarEngine] Parallel scan started for {len(symbols)} symbols.")
            
            results = []
            
            # ThreadPoolExecutor (Max 5 iş parçacığı)
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(self.scan_single_symbol, sym): sym for sym in symbols}
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    if res:
                        results.append(res)
            
            self._save_results_to_db(results)
            self.is_scanning = False
            logger.info("[RadarEngine] Parallel scan finished.")
            
        t = threading.Thread(target=scan_task, daemon=True)
        t.start()
        return True

    def _save_results_to_db(self, results: List[Dict[str, Any]]):
        """Tarama sonuçlarını veritabanına yazar."""
        conn = self.db.get_connection()
        try:
            c = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for res in results:
                sym = res["sym"]
                ai_report = res["ai_report"]
                best_warrant = res["best_warrant"]
                last_row = res["df_1d_last"]
                
                # scan_results güncelle
                c.execute("""
                    INSERT INTO scan_results (
                        symbol, total_score, opportunity_level, eta, stop_eta, 
                        risk_reward, trade_quality, success_prob, trade_type, warrant_code, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        total_score=excluded.total_score,
                        opportunity_level=excluded.opportunity_level,
                        eta=excluded.eta,
                        stop_eta=excluded.stop_eta,
                        risk_reward=excluded.risk_reward,
                        trade_quality=excluded.trade_quality,
                        success_prob=excluded.success_prob,
                        trade_type=excluded.trade_type,
                        warrant_code=excluded.warrant_code,
                        updated_at=excluded.updated_at
                """, (
                    sym, ai_report['Total_Score'], ai_report['Opportunity_Level'],
                    ai_report['ETA'], ai_report.get('Stop_ETA', ''), ai_report.get('Risk_Reward', ''),
                    ai_report.get('Trade_Quality', 0), ai_report['Success_Probability'],
                    ai_report['Trade_Type'], best_warrant, now
                ))
                
                # signals_history kaydı (Eğer çok güçlüyse)
                if ai_report['Total_Score'] >= 70:
                    c.execute("SELECT id FROM signals_history WHERE symbol=? AND status='PENDING'", (sym,))
                    if not c.fetchone():
                        r1 = last_row.get('R1', float(last_row['close']) * 1.05)
                        s1 = last_row.get('S1', float(last_row['close']) * 0.95)
                        c.execute("""
                            INSERT INTO signals_history (
                                symbol, signal_date, trade_type, entry_price, target_price, stop_loss, confidence_score
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (sym, now, ai_report['Trade_Type'], float(last_row['close']), float(r1), float(s1), ai_report['Total_Score']))
                        
            conn.commit()
        except Exception as e:
            logger.error(f"[RadarEngine] Error saving results: {e}")
        finally:
            conn.close()
