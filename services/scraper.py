import yfinance as yf
import pandas as pd
import numpy as np
from database.db_manager import DBManager
from utils.logger import logger
from utils.exceptions import DataFetchError
from config.constants import INTERVAL_1D, INTERVAL_4H, INTERVAL_1H, INTERVAL_15M, INTERVAL_5M

class Scraper:
    def __init__(self):
        self.db = DBManager()

    def fetch_data(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        logger.info(f"Fetching data for {symbol} (period={period}, interval={interval})")
        try:
            # Handle 4h interval specifically by resampling 1h
            yf_interval = "1h" if interval == INTERVAL_4H else interval
            yf_period = "1mo" if interval == INTERVAL_4H else period
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=yf_period, interval=yf_interval, repair=True)
            
            if df.empty:
                logger.warning(f"No data found for {symbol} at {interval}")
                return df
                
            # Veri Doğrulama (Data Validation)
            df = self._validate_and_clean_data(df)
            
            # Resample 1h to 4h if needed
            if interval == INTERVAL_4H and not df.empty:
                df = self._resample_to_4h(df)
                
            if not df.empty:
                self.db.insert_stock_data(df, symbol, interval)
                logger.info(f"Successfully saved {len(df)} records for {symbol} at {interval}")
                
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            raise DataFetchError(f"Failed to fetch {symbol} data: {e}")

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Veri doğrulama ve temizleme işlemleri (Modül 2.10)"""
        # Sütun isimlerini küçük harfe çevir
        df.columns = [c.lower() for c in df.columns]
        
        # Sadece gerekli sütunları tut
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            logger.warning(f"Missing columns in downloaded data: {missing}")
            for m in missing:
                df[m] = 0.0 if m != 'volume' else 0

        # Eksik veya NaN verileri temizle
        # Kapanış fiyatı eksikse önceki günün kapanışını al (Forward Fill)
        df['close'] = df['close'].ffill()
        df['open'] = df['open'].fillna(df['close'])
        df['high'] = df['high'].fillna(df['close'])
        df['low'] = df['low'].fillna(df['close'])
        df['volume'] = df['volume'].fillna(0)
        
        # Tarih index'inin saat dilimini kaldır (SQLite'a temiz yazmak için)
        if df.index.tz is not None:
            df.index = df.index.tz_convert(None)
            
        return df

    def _resample_to_4h(self, df: pd.DataFrame) -> pd.DataFrame:
        """1 saatlik veriyi 4 saatlik veriye çevirir"""
        # Ensure index is datetime
        df.index = pd.to_datetime(df.index)
        
        # OHLCV Resampling kuralları
        resample_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        # 4 Saatlik periyotlara böl (BIST saatlerine uydurmak için base parametresi ayarlanabilir)
        # BIST 10:00 - 18:00 arası açık.
        resampled_df = df.resample('4h', offset='2h').agg(resample_dict).dropna()
        return resampled_df

    def fetch_index_data(self, period: str = "1mo", interval: str = "1d"):
        """Endeks (XU100) verisini çeker (Modül 2.9)"""
        return self.fetch_data("XU100.IS", period, interval)

    def fetch_all_intervals_for_symbol(self, symbol: str):
        """Bir hisse için tüm periyotları çeker (1D, 4H, 1H, 15M, 5M)"""
        intervals_to_fetch = [
            ("1y", INTERVAL_1D),
            ("1mo", INTERVAL_4H),  # Actually fetches 1mo of 1h data and resamples
            ("1mo", INTERVAL_1H),
            ("5d", INTERVAL_15M),
            ("5d", INTERVAL_5M)
        ]
        for period, interval in intervals_to_fetch:
            self.fetch_data(symbol, period, interval)
            
        # Aynı periyotlarda endeks verisini de çek (Korelasyon için gerekli)
        for period, interval in intervals_to_fetch:
            self.fetch_index_data(period, interval)
