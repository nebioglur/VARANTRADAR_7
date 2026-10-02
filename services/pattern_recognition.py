import pandas as pd
import numpy as np

class PatternRecognitionEngine:
    """
    Geometrik Fiyat Formasyonlarını tespit eden kural tabanlı motor. (Modül 7)
    Tespit için önceden SupportResistanceAnalyzer.detect_swing_high_low() çalıştırılmış olmalıdır.
    """
    
    @staticmethod
    def detect_all_patterns(df: pd.DataFrame) -> pd.DataFrame:
        if 'Swing_High' not in df.columns:
            return df
            
        df = PatternRecognitionEngine._detect_double_top_bottom(df)
        df = PatternRecognitionEngine._detect_head_and_shoulders(df)
        df = PatternRecognitionEngine._detect_triangles_and_wedges(df)
        return df

    @staticmethod
    def _detect_double_top_bottom(df: pd.DataFrame, tolerance: float = 0.02) -> pd.DataFrame:
        """ İkili Tepe ve İkili Dip Formasyonu Tespiti """
        df['Double_Top'] = False
        df['Double_Bottom'] = False
        
        highs = df[df['Swing_High']].copy()
        lows = df[df['Swing_Low']].copy()
        
        # Son 2 tepe birbirine yakınsa (İkili Tepe)
        if len(highs) >= 2:
            last_highs = highs.tail(2)
            h1, h2 = last_highs['high'].values
            if abs(h1 - h2) / max(h1, h2) <= tolerance:
                # Aradaki dibin kırılıp kırılmadığını kontrol et (Breakout)
                df.loc[df.index[-1], 'Double_Top'] = True
                
        # Son 2 dip birbirine yakınsa (İkili Dip)
        if len(lows) >= 2:
            last_lows = lows.tail(2)
            l1, l2 = last_lows['low'].values
            if abs(l1 - l2) / max(l1, l2) <= tolerance:
                df.loc[df.index[-1], 'Double_Bottom'] = True
                
        return df

    @staticmethod
    def _detect_head_and_shoulders(df: pd.DataFrame) -> pd.DataFrame:
        """ OBO ve TOBO Formasyonları Tespiti """
        df['OBO'] = False
        df['TOBO'] = False
        
        highs = df[df['Swing_High']]
        lows = df[df['Swing_Low']]
        
        # OBO: Sol Omuz < Baş > Sağ Omuz
        if len(highs) >= 3:
            h1, h2, h3 = highs['high'].tail(3).values
            if h1 < h2 and h3 < h2 and abs(h1 - h3) / max(h1, h3) < 0.05:
                df.loc[df.index[-1], 'OBO'] = True
                
        # TOBO: Sol Omuz > Baş < Sağ Omuz
        if len(lows) >= 3:
            l1, l2, l3 = lows['low'].tail(3).values
            if l1 > l2 and l3 > l2 and abs(l1 - l3) / max(l1, l3) < 0.05:
                df.loc[df.index[-1], 'TOBO'] = True
                
        return df

    @staticmethod
    def _detect_triangles_and_wedges(df: pd.DataFrame) -> pd.DataFrame:
        """ Üçgen, Takoz, Bayrak Formasyonları (Yükselen/Alçalan Trend Çizgileri Kesişimi) """
        df['Bullish_Flag_Pennant'] = False
        df['Bearish_Flag_Pennant'] = False
        
        highs = df[df['Swing_High']]
        lows = df[df['Swing_Low']]
        
        if len(highs) >= 3 and len(lows) >= 3:
            last_3_highs = highs['high'].tail(3).values
            last_3_lows = lows['low'].tail(3).values
            
            # Yüksekler alçalıyor, dipler yükseliyor -> Simetrik Üçgen / Flama
            if (last_3_highs[0] > last_3_highs[1] > last_3_highs[2]) and \
               (last_3_lows[0] < last_3_lows[1] < last_3_lows[2]):
                df.loc[df.index[-1], 'Bullish_Flag_Pennant'] = True # Aslında yöne göre değişir, basitleştirildi
                
        return df
