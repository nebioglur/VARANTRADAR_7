import pandas as pd
import numpy as np
from typing import Dict, Any

class RotationEngine:
    """
    Sermaye Rotasyonu (Capital Rotation) ve Sektörel Göreceli Güç (Relative Strength) analizi.
    Akıllı paranın hangi sektörden çıkıp hangisine girdiğini tespit eder.
    """
    
    @staticmethod
    def calculate_relative_strength(asset_df: pd.DataFrame, benchmark_df: pd.DataFrame, window: int = 20) -> pd.Series:
        """
        Göreceli Güç (Relative Strength - RS) hesabı (RSI değil).
        RS = Asset Price / Benchmark Price
        Eğer RS eğrisi yükseliyorsa varlık endeksten daha iyi performans gösteriyor demektir (Leading).
        """
        if asset_df.empty or benchmark_df.empty:
            return pd.Series(dtype=float)
            
        # Fiyatları hizala
        df = pd.concat([asset_df['close'], benchmark_df['close']], axis=1).dropna()
        df.columns = ['Asset', 'Benchmark']
        
        if df.empty:
            return pd.Series(dtype=float)
            
        rs_line = df['Asset'] / df['Benchmark']
        
        # RS Momentum (RS çizgisinin hareketli ortalaması ve eğimi)
        rs_ma = rs_line.rolling(window=window).mean()
        rs_momentum = (rs_line / rs_ma) - 1  # 0'ın üstü momentum pozitif
        
        return rs_momentum

    @staticmethod
    def analyze_rotation(sector_prices: Dict[str, pd.DataFrame], benchmark_df: pd.DataFrame) -> pd.DataFrame:
        """
        Birden fazla sektör/hisse için Rotasyon Skoru ve Capital Flow (Para Girişi) tahmini üretir.
        """
        results = []
        if benchmark_df.empty:
            return pd.DataFrame()
            
        for name, df in sector_prices.items():
            if df.empty or len(df) < 20:
                continue
                
            rs_momentum = RotationEngine.calculate_relative_strength(df, benchmark_df)
            if rs_momentum.empty:
                continue
                
            latest_rs = rs_momentum.iloc[-1]
            
            # Para Akışı (Capital Flow) Proxy - Basit Trend/Hacim
            # Eğer fiyat artıyor ve Hacim de ortalamanın üstündeyse para giriyor
            avg_vol = df['volume'].rolling(20).mean().iloc[-1] if 'volume' in df.columns else 1
            latest_vol = df['volume'].iloc[-1] if 'volume' in df.columns else 1
            vol_ratio = latest_vol / avg_vol if avg_vol > 0 else 1
            
            price_change_5d = (df['close'].iloc[-1] / df['close'].iloc[-5]) - 1 if len(df) >= 5 else 0
            
            flow_status = "NEUTRAL"
            if price_change_5d > 0 and vol_ratio > 1.2:
                flow_status = "INFLOW (Para Girişi)"
            elif price_change_5d < 0 and vol_ratio > 1.2:
                flow_status = "OUTFLOW (Para Çıkışı)"
                
            # Kadran Belirleme (Leading, Weakening, Lagging, Improving)
            quadrant = "LAGGING"
            if latest_rs > 0 and price_change_5d > 0:
                quadrant = "LEADING (Lider)"
            elif latest_rs > 0 and price_change_5d < 0:
                quadrant = "WEAKENING (Zayıflayan)"
            elif latest_rs < 0 and price_change_5d < 0:
                quadrant = "LAGGING (Geride Kalan)"
            elif latest_rs < 0 and price_change_5d > 0:
                quadrant = "IMPROVING (Gelişen)"
                
            results.append({
                "Sector": name,
                "Relative_Strength": round(latest_rs * 100, 2), # Yüzde bazında
                "Rotation_Quadrant": quadrant,
                "Capital_Flow": flow_status
            })
            
        if not results:
            return pd.DataFrame()
            
        res_df = pd.DataFrame(results)
        res_df.set_index("Sector", inplace=True)
        # Relative Strength'e göre sırala (En güçlüler üstte)
        return res_df.sort_values(by="Relative_Strength", ascending=False)
