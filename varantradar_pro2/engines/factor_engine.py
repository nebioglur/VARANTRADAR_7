import pandas as pd
import numpy as np
from typing import Dict, Any

class FactorEngine:
    """
    Hisse senetleri için "Smart Beta" ve Kurumsal Faktör (Factor Investing) skorlarını hesaplar.
    Momentum, Volatility, Liquidity (Size vekil), Trend Quality gibi faktörleri OHLCV'den üretir.
    Fundamental (Temel) veriler (F/K, PD/DD) entegre edildiğinde Value ve Growth faktörleri açılacaktır.
    """
    
    @staticmethod
    def calculate_factors(df: pd.DataFrame) -> Dict[str, float]:
        """
        Girdi: Günlük OHLCV DataFrame (Bir hisse için).
        Çıktı: Faktör skorları (1-100 arası normalize edilebilir veya raw)
        """
        if df.empty or len(df) < 252:
            return {"error": "Faktör analizi için en az 1 yıllık (252 gün) veri gereklidir."}
            
        returns = df['close'].pct_change().dropna()
        
        # 1. Momentum Factor (12-aylık getiri, son 1 ay hariç - klasik Fama-French momentum)
        # Basitleştirilmiş: Son 1 Yıl Getirisi - Son 1 Ay Getirisi
        close_today = df['close'].iloc[-1]
        close_1m_ago = df['close'].iloc[-21] if len(df) >= 21 else df['close'].iloc[0]
        close_1y_ago = df['close'].iloc[-252]
        
        momentum_1y = (close_1m_ago / close_1y_ago) - 1 # 12M-1M Momentum
        short_term_mom = (close_today / close_1m_ago) - 1 # 1M Momentum (Reversal etkisi için)
        
        # 2. Low Volatility Factor (Düşük volatilite yüksek skor alır)
        annual_volatility = returns.std() * np.sqrt(252)
        # Ters orantı: Volatilite ne kadar düşükse skor o kadar iyidir
        low_vol_score = 1.0 / annual_volatility if annual_volatility > 0 else 0
        
        # 3. Quality Factor (Sharpe/Sortino benzeri trend kalitesi)
        downside_returns = returns[returns < 0]
        downside_volatility = downside_returns.std() * np.sqrt(252)
        trend_quality = returns.mean() / downside_volatility if downside_volatility > 0 else 0
        
        # 4. Size / Liquidity Factor (Hacim Bazlı Vekil)
        # Median günlük işlem hacmi (TL bazında)
        if 'volume' in df.columns:
            median_volume = (df['volume'] * df['close']).median()
        else:
            median_volume = 0
            
        # Z-Score veya Normalize edilebilir (Burada raw değerler döndürülüyor, 
        # Multi-asset karşılaştırmasında Z-Score alınmalıdır)
        
        return {
            "Momentum_12M_1M": round(momentum_1y, 4),
            "Momentum_1M": round(short_term_mom, 4),
            "Annual_Volatility": round(annual_volatility, 4),
            "Trend_Quality": round(trend_quality, 4),
            "Median_Liquidity": round(median_volume, 2),
            # Fundamental eklenecekler: Value (P/E), Growth (EPS Growth), Dividend
        }
        
    @staticmethod
    def calculate_multi_asset_factors(prices_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Birden fazla hissenin faktör skorlarını hesaplar ve Z-Score ile (0-100) arası derecelendirir.
        """
        results = []
        for sym, df in prices_dict.items():
            factors = FactorEngine.calculate_factors(df)
            if "error" not in factors:
                factors['symbol'] = sym
                results.append(factors)
                
        if not results:
            return pd.DataFrame()
            
        res_df = pd.DataFrame(results)
        res_df.set_index('symbol', inplace=True)
        
        # Z-Score Normalizasyonu ve (0-100) Skalası
        # Z = (X - Mu) / Sigma
        # Score = norm.cdf(Z) * 100
        from scipy.stats import norm
        
        # Momentum: Yüksek daha iyi
        z_mom = (res_df['Momentum_12M_1M'] - res_df['Momentum_12M_1M'].mean()) / res_df['Momentum_12M_1M'].std()
        res_df['Momentum_Score'] = norm.cdf(z_mom.fillna(0)) * 100
        
        # Low Volatility: Düşük volatilite daha iyi (O yüzden negatif Z-Score)
        z_vol = (res_df['Annual_Volatility'] - res_df['Annual_Volatility'].mean()) / res_df['Annual_Volatility'].std()
        res_df['Low_Vol_Score'] = norm.cdf(-z_vol.fillna(0)) * 100
        
        # Quality: Yüksek daha iyi
        z_qual = (res_df['Trend_Quality'] - res_df['Trend_Quality'].mean()) / res_df['Trend_Quality'].std()
        res_df['Quality_Score'] = norm.cdf(z_qual.fillna(0)) * 100
        
        # Multi-Factor Score (Eşit ağırlıklı kompozit skor)
        res_df['Multi_Factor_Score'] = (res_df['Momentum_Score'] + res_df['Low_Vol_Score'] + res_df['Quality_Score']) / 3
        
        return res_df.round(2)
