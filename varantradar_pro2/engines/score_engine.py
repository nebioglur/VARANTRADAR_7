import pandas as pd
from typing import Dict, Any

class ScoreEngine:
    """
    Sadece Teknik Analiz ve Puanlama metriklerini hesaplar.
    """
    
    def calculate_scores(self, df_1d: pd.DataFrame, df_4h: pd.DataFrame = None) -> Dict[str, Any]:
        """
        CFG-02 (Multi-Timeframe) destekli puanlama algoritması.
        """
        if df_1d is None or len(df_1d) < 14:
            return {"Total_Score": 0, "Details": {}}
            
        last_row = df_1d.iloc[-1]
        scores = {
            "Trend": 0,
            "Momentum": 0,
            "Volatility": 0,
            "Volume": 0,
            "Multi_Timeframe": 0
        }
        
        # 1. Trend (0-35)
        if 'EMA' in df_1d.columns and last_row['close'] > last_row['EMA']:
            scores["Trend"] += 15
        if 'MACD' in df_1d.columns and last_row['MACD'] > 0:
            scores["Trend"] += 10
        if 'MACD_Signal' in df_1d.columns and last_row['MACD'] > last_row['MACD_Signal']:
            scores["Trend"] += 10
            
        # 2. Momentum (0-25)
        if 'RSI' in df_1d.columns:
            if 40 <= last_row['RSI'] <= 60:
                scores["Momentum"] += 25
            elif 30 <= last_row['RSI'] < 40 or 60 < last_row['RSI'] <= 70:
                scores["Momentum"] += 15
                
        # 3. Volatilite / Sıkışma (0-20)
        if 'BB_Lower' in df_1d.columns and 'BB_Upper' in df_1d.columns:
            bb_width = (last_row['BB_Upper'] - last_row['BB_Lower']) / last_row['close']
            if bb_width < 0.10:  # Sıkışma var
                scores["Volatility"] += 20
            elif bb_width < 0.15:
                scores["Volatility"] += 10
                
        # 4. Hacim (0-20)
        # Hacim verisi simülasyonu / mock puan
        scores["Volume"] += 15 
        
        # 5. Multi-Timeframe CFG-02 (+20 Bonus)
        if df_4h is not None and not df_4h.empty and len(df_4h) > 1:
            last_4h = df_4h.iloc[-1]
            if 'EMA' in df_4h.columns and last_4h['close'] > last_4h['EMA']:
                scores["Multi_Timeframe"] += 10
            if 'MACD' in df_4h.columns and last_4h['MACD'] > 0:
                scores["Multi_Timeframe"] += 10
                
        total_score = sum(scores.values())
        # Cap at 100
        total_score = min(100, total_score)
        
        return {
            "Total_Score": total_score,
            "Details": scores
        }
