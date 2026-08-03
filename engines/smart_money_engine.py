import pandas as pd
import numpy as np
from typing import Dict, Any

class SmartMoneyEngine:
    """
    OHLCV (Açılış, Kapanış, Yüksek, Düşük, Hacim) verilerini kullanarak
    kurumsal yatırımcıların (Smart Money) gizli para giriş/çıkışlarını analiz eder.
    """
    
    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.Series:
        """On-Balance Volume (OBV)"""
        if df.empty or 'close' not in df.columns or 'volume' not in df.columns:
            return pd.Series(dtype=float)
            
        close = df['close']
        volume = df['volume']
        
        direction = np.where(close > close.shift(1), 1, np.where(close < close.shift(1), -1, 0))
        obv = (direction * volume).cumsum()
        return obv

    @staticmethod
    def calculate_mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Money Flow Index (MFI) - Hacim ağırlıklı RSI"""
        if df.empty or len(df) <= period:
            return pd.Series(dtype=float)
            
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        raw_money_flow = typical_price * df['volume']
        
        positive_flow = np.where(typical_price > typical_price.shift(1), raw_money_flow, 0.0)
        negative_flow = np.where(typical_price < typical_price.shift(1), raw_money_flow, 0.0)
        
        positive_flow_series = pd.Series(positive_flow, index=df.index)
        negative_flow_series = pd.Series(negative_flow, index=df.index)
        
        pos_flow_sum = positive_flow_series.rolling(window=period).sum()
        neg_flow_sum = negative_flow_series.rolling(window=period).sum()
        
        # Sifira bolme hatasini engelleme
        money_ratio = pos_flow_sum / neg_flow_sum.replace(0, np.nan)
        mfi = 100 - (100 / (1 + money_ratio))
        
        # Eger negative_flow 0 ise, MFI 100 olmali
        mfi = mfi.fillna(100.0)
        return mfi

    @staticmethod
    def calculate_accumulation_distribution(df: pd.DataFrame) -> pd.Series:
        """Accumulation/Distribution (A/D) Line"""
        if df.empty:
            return pd.Series(dtype=float)
            
        # Money Flow Multiplier
        mfm_denominator = (df['high'] - df['low'])
        # Eger High == Low ise 0 a bolme hatasindan kacin
        mfm = np.where(mfm_denominator == 0, 0, ((df['close'] - df['low']) - (df['high'] - df['close'])) / mfm_denominator)
        
        # Money Flow Volume
        mfv = mfm * df['volume']
        
        # A/D Line (Cumulative)
        ad_line = mfv.cumsum()
        return pd.Series(ad_line, index=df.index)
        
    @staticmethod
    def calculate_cmf(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Chaikin Money Flow (CMF)"""
        if df.empty or len(df) <= period:
            return pd.Series(dtype=float)
            
        mfm_denominator = (df['high'] - df['low'])
        mfm = np.where(mfm_denominator == 0, 0, ((df['close'] - df['low']) - (df['high'] - df['close'])) / mfm_denominator)
        mfv = pd.Series(mfm * df['volume'], index=df.index)
        
        cmf = mfv.rolling(window=period).sum() / df['volume'].rolling(window=period).sum()
        return cmf
        
    @staticmethod
    def analyze_smart_money(df: pd.DataFrame) -> Dict[str, Any]:
        """Tüm göstergeleri hesaplayıp genel bir durum özeti döner."""
        if df.empty or len(df) < 21:
            return {"error": "Yeterli veri yok (min 21 bar)."}
            
        obv = SmartMoneyEngine.calculate_obv(df)
        mfi = SmartMoneyEngine.calculate_mfi(df)
        ad_line = SmartMoneyEngine.calculate_accumulation_distribution(df)
        cmf = SmartMoneyEngine.calculate_cmf(df)
        
        latest_obv = obv.iloc[-1]
        prev_obv = obv.iloc[-5] if len(obv) >= 5 else obv.iloc[0]
        obv_trend = "UP" if latest_obv > prev_obv else "DOWN"
        
        latest_mfi = mfi.iloc[-1]
        mfi_status = "OVERSOLD (Akümülasyon Fırsatı)" if latest_mfi < 20 else ("OVERBOUGHT (Dağıtım Riski)" if latest_mfi > 80 else "NEUTRAL")
        
        latest_cmf = cmf.iloc[-1]
        cmf_status = "STRONG INFLOW (Para Girişi)" if latest_cmf > 0.15 else ("STRONG OUTFLOW (Para Çıkışı)" if latest_cmf < -0.15 else "NEUTRAL")
        
        # Sinyal Sentezi
        smart_score = 50
        if obv_trend == "UP": smart_score += 15
        else: smart_score -= 15
        
        if latest_mfi < 30: smart_score += 10 # Ucuzluk/Toplama
        elif latest_mfi > 70: smart_score -= 15 # Pahalı/Dağıtım
        
        if latest_cmf > 0.1: smart_score += 25
        elif latest_cmf < -0.1: smart_score -= 25
        
        smart_score = min(100, max(0, smart_score))
        
        return {
            "OBV_Trend_5D": obv_trend,
            "MFI_Value": round(latest_mfi, 2),
            "MFI_Status": mfi_status,
            "CMF_Value": round(latest_cmf, 3),
            "CMF_Status": cmf_status,
            "Smart_Money_Score": smart_score,
            "Verdict": "AKÜMÜLASYON (Büyük Para Topluyor)" if smart_score >= 70 else ("DAĞITIM (Büyük Para Çıkıyor)" if smart_score <= 30 else "KARARSIZ (Baskı Yok)")
        }
