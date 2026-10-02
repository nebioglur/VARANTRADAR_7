import pandas as pd
from data.source_manager import DataSourceManager, ValidatedDataResult

class DataPipeline:
    """
    CFG-03.1 Enhanced Data Architecture (Boru Hattı)
    
    Artık tek bir provider'a bağlı değil.
    DataSourceManager üzerinden çalışır:
    - Multi-source failover
    - Data validation
    - 3 katmanlı cache
    - Health monitoring
    
    Eski API uyumluluğu korunur (get_clean_data hâlâ çalışır).
    """
    
    def __init__(self, provider=None):
        """
        Geriye uyumluluk: provider parametresi verilirse eski mod,
        verilmezse yeni DataSourceManager modu çalışır.
        """
        self.source_manager = DataSourceManager()
        self._legacy_provider = provider
        
    def get_clean_data(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        """
        Geriye uyumlu API. Eski kodlar bunu çağırmaya devam edebilir.
        Arka planda DataSourceManager çalışır.
        """
        result = self.get_validated_data(symbol, period, interval)
        if result.is_valid:
            return self._clean_data(result.df)
        else:
            # Legacy davranış: boş DataFrame dön
            return pd.DataFrame()
    
    def get_validated_data(self, symbol: str, period: str = "1mo", interval: str = "1d") -> ValidatedDataResult:
        """
        CFG-03.1 Yeni API.
        Doğrulanmış veri + kalite skoru + kaynak bilgisi döner.
        """
        result = self.source_manager.fetch_validated(symbol, period, interval)
        
        if result.is_valid:
            result.df = self._clean_data(result.df)
        
        return result
    
    def get_health_report(self) -> dict:
        """Provider sağlık dashboard verisi."""
        return self.source_manager.get_health_report()
    
    def get_data_logs(self, count: int = 20) -> list:
        """Son veri çekme logları."""
        return self.source_manager.get_logs(count)
        
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Veri içerisindeki boşlukları onarır ve kolon isimlerini standartlaştırır."""
        if df is None or df.empty:
            return pd.DataFrame()
        
        # MultiIndex kolon kontrolü (YFinance bazen MultiIndex döner)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Kolonları string'e çevirip küçük harfe çevir (Standartlaştırma)
        df.columns = [str(c).lower() for c in df.columns]
        
        # Zorunlu kolon kontrolü
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0.0 if col != 'volume' else 0
                
        # Boş (NaN) verileri doldurma (Forward Fill)
        df['close'] = df['close'].ffill()
        df['open'] = df['open'].fillna(df['close'])
        df['high'] = df['high'].fillna(df['close'])
        df['low'] = df['low'].fillna(df['close'])
        df['volume'] = df['volume'].fillna(0)
        
        # İstenmeyen kolonları at (Sadece OHLCV kalsın)
        df = df[required_cols]
        
        return df
