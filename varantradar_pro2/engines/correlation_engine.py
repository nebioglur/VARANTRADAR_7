import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple

class CorrelationEngine:
    """
    Çoklu varlık portföyleri için Korelasyon ve Çeşitlendirme (Diversification) analizleri yapar.
    Hedge Fonların risk yönetimi (Risk Parity vb.) için temel teşkil eder.
    """
    
    @staticmethod
    def calculate_correlation_matrix(price_df: pd.DataFrame, method: str = 'pearson') -> pd.DataFrame:
        """
        Girdi: Fiyatların DataFrame'i (Her sütun bir varlık).
        Çıktı: Günlük getiriler üzerinden hesaplanan Korelasyon matrisi.
        """
        if price_df.empty or len(price_df.columns) < 2:
            return pd.DataFrame()
            
        returns = price_df.pct_change().dropna()
        return returns.corr(method=method)

    @staticmethod
    def calculate_rolling_correlation(price_df: pd.DataFrame, asset1: str, asset2: str, window: int = 30) -> pd.Series:
        """İki varlık arasındaki zaman içindeki (Rolling) korelasyon değişimini hesaplar."""
        if price_df.empty or asset1 not in price_df.columns or asset2 not in price_df.columns:
            return pd.Series(dtype=float)
            
        returns = price_df.pct_change().dropna()
        return returns[asset1].rolling(window=window).corr(returns[asset2])

    @staticmethod
    def calculate_diversification_score(weights: Dict[str, float], cov_matrix: pd.DataFrame) -> float:
        """
        Portfolio Diversification Ratio (PDR)
        PDR = (Ağırlıklandırılmış ortalama varlık volatilitesi) / (Portföy Volatilitesi)
        Ne kadar yüksekse, çeşitlendirme o kadar başarılı demektir (Genelde > 1.0)
        """
        if not weights or cov_matrix.empty:
            return 0.0
            
        w = np.array([weights.get(col, 0) for col in cov_matrix.columns])
        if w.sum() == 0:
            return 0.0
            
        # Varlıkların bireysel volatiliteleri (Kovaryans matrisinin köşegeni)
        asset_vols = np.sqrt(np.diag(cov_matrix))
        weighted_asset_vols = np.sum(w * asset_vols)
        
        # Portföyün toplam volatilitesi (w.T * Cov * w)
        portfolio_variance = np.dot(w.T, np.dot(cov_matrix, w))
        portfolio_vol = np.sqrt(portfolio_variance)
        
        if portfolio_vol == 0:
            return 0.0
            
        diversification_ratio = weighted_asset_vols / portfolio_vol
        
        # UI için normalize edebiliriz, 1.0 (Hiç çeşitlendirme yok) ile 3.0 (Mükemmel) arası
        # Burada Raw Ratio döndürüyoruz.
        return round(diversification_ratio, 2)
        
    @staticmethod
    def get_correlation_alerts(corr_matrix: pd.DataFrame, threshold: float = 0.85) -> list:
        """Aşırı yüksek korelasyona sahip (yani portföyde gizli risk yaratan) ikilileri bulur."""
        alerts = []
        if corr_matrix.empty:
            return alerts
            
        cols = corr_matrix.columns
        for i in range(len(cols)):
            for j in range(i+1, len(cols)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) >= threshold:
                    alerts.append({
                        "asset1": cols[i],
                        "asset2": cols[j],
                        "correlation": round(corr_val, 2),
                        "warning": "HIGH_CORRELATION" if corr_val > 0 else "HIGH_INVERSE_CORRELATION"
                    })
        return alerts
