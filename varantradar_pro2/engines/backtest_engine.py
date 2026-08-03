import pandas as pd
import numpy as np
from typing import Dict, Any

class BacktestEngine:
    """
    Kendi yazdığımız Numpy/Pandas tabanlı hızlı, vektörel (vectorized) backtest motoru.
    Gelen Al(1)/Sat(-1) sinyallerine göre sanal portföy büyümesini hesaplar.
    """
    
    def __init__(self, initial_capital: float = 100000.0, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission

    def run_backtest(self, df: pd.DataFrame, signals: pd.Series) -> pd.DataFrame:
        """
        Sinyaller: 1 (Al), 0 (Bekle), -1 (Sat/Açığa Sat veya Nakite Geç).
        Bu versiyonda basitçe 1 = Long Pozisyonda ol, 0/ -1 = Nakitte ol (Long-only varsayımı).
        """
        # Sinyalleri 1 ve 0'a zorla (Long Only Stratejisi için)
        positions = np.where(signals > 0, 1, 0)
        
        # DataFrame kopyası oluştur ve pozisyonları ekle
        bt_df = pd.DataFrame(index=df.index)
        bt_df['close'] = df['close']
        bt_df['position'] = positions
        
        # Getiriler (Returns)
        bt_df['asset_returns'] = bt_df['close'].pct_change()
        
        # İşlem Gecikmesi (Signal delay): Sinyal geldiği günün kapanışından (veya ertesi gün açılış) işleme girilir.
        # Basitlik için sinyal sonrası (shift(1)) getiriyi hesaplıyoruz.
        bt_df['strategy_returns'] = bt_df['asset_returns'] * bt_df['position'].shift(1)
        
        # Komisyon Hesaplanması (Pozisyon değişimlerinde)
        bt_df['trades'] = bt_df['position'].diff().abs()
        bt_df['commission_cost'] = bt_df['trades'] * self.commission
        bt_df['strategy_returns'] = bt_df['strategy_returns'] - bt_df['commission_cost'].fillna(0)
        
        # Equity Curve (Sermaye Büyümesi)
        bt_df['strategy_equity'] = self.initial_capital * (1 + bt_df['strategy_returns'].fillna(0)).cumprod()
        bt_df['asset_equity'] = self.initial_capital * (1 + bt_df['asset_returns'].fillna(0)).cumprod()
        
        return bt_df
