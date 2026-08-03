import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from utils.logger import logger
from services.analyzer import Analyzer
from services.ai_decision_engine import AIDecisionEngine

class RadarEngine:
    """
    VarantRadar Pro V3 - BIST Radar Sistemi
    Geniş çaplı piyasa taraması ve filtreleme motoru.
    """
    def __init__(self):
        self.analyzer = Analyzer()

    def run_radar(self, symbols: List[str], max_workers: int = 10, min_volume: float = 1000000) -> pd.DataFrame:
        """
        Verilen hisse listesini çoklu iş parçacığı (Multi-threading) ile tarar. (Modül 1 & 2)
        """
        logger.info(f"V3 Radar başlatılıyor. Toplam Hisse: {len(symbols)}")
        results = []
        
        # 1. Hızlı Veri Çekimi ve Ön Filtre (Modül 3)
        # Sadece Kapanış ve Hacim verilerini çekerek "Ölü" hisseleri eliyoruz.
        # Yahoo Finance'den bulk (toplu) veri çekimi daha güvenlidir.
        try:
            # yfinance bulk download (string format: "AAPL MSFT GOOG")
            tickers_str = " ".join(symbols)
            bulk_data = yf.download(tickers_str, period="1mo", interval="1d", group_by="ticker", auto_adjust=True, progress=False)
            
            valid_symbols = []
            
            if len(symbols) == 1:
                # yfinance returns different structure for single ticker
                if not bulk_data.empty:
                    valid_symbols.append(symbols[0])
            else:
                for symbol in symbols:
                    if symbol in bulk_data.columns.levels[0]:
                        stock_df = bulk_data[symbol]
                        # Dropna to check if it has recent data
                        stock_df = stock_df.dropna(subset=['Close', 'Volume'])
                        if not stock_df.empty and len(stock_df) > 10:
                            avg_vol = stock_df['Volume'].tail(5).mean()
                            close_price = stock_df['Close'].iloc[-1]
                            
                            # Modül 3: İlk Filtre (Hacim ve Fiyat)
                            # Ortalama günlük hacim > min_volume ve Fiyat > 1 TL
                            if avg_vol >= min_volume and close_price > 1.0:
                                valid_symbols.append(symbol)
                                
            logger.info(f"Ön filtreden geçen hisse sayısı: {len(valid_symbols)}")
            
        except Exception as e:
            logger.error(f"Toplu veri çekiminde hata: {e}")
            return pd.DataFrame()

        # 2. Teknik Filtre ve AI Puanlama (Modül 4 & 7)
        # Sadece hayatta kalan (hacimli) hisselere detaylı indikatör ve AI analizi uyguluyoruz.
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {executor.submit(self._analyze_single_stock, sym): sym for sym in valid_symbols}
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"{symbol} analizi sırasında hata: {e}")
                    
        # 3. Sonuçları Sıralama (Modül 1.4 & 7)
        if not results:
            return pd.DataFrame()
            
        df_results = pd.DataFrame(results)
        # AI Puanına göre büyükten küçüğe sırala
        df_results = df_results.sort_values(by="Puan", ascending=False).reset_index(drop=True)
        
        # Akıllı Filtre Etiketleri (Modül 9)
        df_results = self._apply_smart_labels(df_results)
        
        return df_results

    def _analyze_single_stock(self, symbol: str) -> Dict[str, Any]:
        """Tek bir hisseyi detaylı analiz eder ve V2 Karar Motorundan geçirir."""
        # Veriyi zaten DB'ye yazdırmıyoruz radar sırasında, direkt anlık analiz yapıyoruz.
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="6mo", interval="1d", repair=True)
            if df.empty or len(df) < 50:
                return None
                
            # Sütunları küçük harfe çevir (Analyzer beklentisi)
            df.columns = [c.lower() for c in df.columns]
            df.reset_index(inplace=True)
            df.rename(columns={'date': 'date', 'index': 'date'}, inplace=True)
            
            # Analyzer çalıştır
            df_analyzed = self.analyzer.calculate_indicators(symbol, "1d")
            
            # Eğer db'de yoksa veya hesaplanamadıysa manuel yfinance verisinden hesapla
            if df_analyzed.empty and not df.empty:
                # Analyzer metodu aslında DB'den okuyor. Radar için geçici bir workaround yapalım.
                # DB'ye insert_stock_data kullanabiliriz ama yavaşlatır.
                # Şimdilik DB'ye yazalım, sonra analiz edelim.
                from database.db_manager import DBManager
                db = DBManager()
                db.insert_stock_data(df, symbol, "1d")
                df_analyzed = self.analyzer.calculate_indicators(symbol, "1d")

            if df_analyzed.empty:
                return None
                
            # V2 Karar Motoruna gönder
            ai_report = AIDecisionEngine.generate_ai_report(df_analyzed, symbol)
            
            if "error" in ai_report:
                return None
                
            return {
                "Hisse": symbol,
                "Fiyat": ai_report['Price'],
                "Puan": ai_report['Total_Score'],
                "Seviye": ai_report['Opportunity_Level'].split(" ")[0], # Sadece Harf (S, A, B)
                "Durum": ai_report['Readiness'],
                "Trend": ai_report['Scores']['Trend'],
                "Momentum": ai_report['Scores']['Momentum'],
                "Olasılık": ai_report['Success_Probability'],
                "İşlem Tipi": ai_report['Trade_Type'],
                "ETA": ai_report['ETA']
            }
        except Exception as e:
            logger.error(f"Hata _analyze_single_stock ({symbol}): {e}")
            return None

    def _apply_smart_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """Modül 9: Akıllı Filtreler (En Güçlü Trend, Dipten Dönüş vb.)"""
        df['Etiket'] = ""
        
        if not df.empty:
            # En Güçlü Trend (Trend puanı en yüksek olan)
            trend_max = df['Trend'].max()
            if trend_max > 0:
                df.loc[df['Trend'] == trend_max, 'Etiket'] += "🔥 Güçlü Trend "
                
            # Günün Hissesi (Puanı en yüksek)
            df.loc[0, 'Etiket'] += "⭐ Günün Fırsatı "
            
        return df
