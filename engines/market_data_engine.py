import yfinance as yf
import pandas as pd
from typing import Optional
from utils.logger import logger
from utils.exceptions import DataFetchError
from config.constants import INTERVAL_1D, INTERVAL_4H

class MarketDataEngine:
    """
    Sadece piyasa verilerini çekmek, doğrulamak ve temizlemekle sorumludur. (Single Responsibility)
    Veritabanına kaydetme işlemini bilmez, sadece veri üretir.
    """
    
    def fetch_data(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        logger.info(f"[MarketDataEngine] Fetching data for {symbol} (period={period}, interval={interval})")
        try:
            yf_interval = "1h" if interval == INTERVAL_4H else interval
            yf_period = "1mo" if interval == INTERVAL_4H else period
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=yf_period, interval=yf_interval, repair=True)
            
            if df.empty:
                logger.warning(f"[MarketDataEngine] No data found for {symbol} at {interval}")
                return df
                
            df = self._validate_and_clean_data(df)
            
            if interval == INTERVAL_4H and not df.empty:
                df = self._resample_to_4h(df)
                
            return df
        except Exception as e:
            logger.error(f"[MarketDataEngine] Error fetching data for {symbol}: {str(e)}")
            return pd.DataFrame()

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [c.lower() for c in df.columns]
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            logger.warning(f"[MarketDataEngine] Rejecting OHLCV data with missing columns: {missing}")
            return pd.DataFrame(columns=required_cols)

        df = df[required_cols].apply(pd.to_numeric, errors='coerce')
        df = df.replace([float('inf'), float('-inf')], pd.NA).dropna(subset=required_cols)
        df = df[(df[['open', 'high', 'low', 'close']] > 0).all(axis=1) & (df['volume'] >= 0)]
        df = df[(df['high'] >= df['low']) & (df['close'] <= df['high']) & (df['close'] >= df['low'])]
        return df

    def _resample_to_4h(self, df: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(df.index, pd.DatetimeIndex):
            return df
            
        conversion = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        # Keep only existing columns
        conversion = {k: v for k, v in conversion.items() if k in df.columns}
        return df.resample('4h', offset='1h').agg(conversion).dropna()
