import pandas as pd
import numpy as np
from typing import Dict, Any

class RiskEngine:
    """
    Sadece Risk ve Volatilite hesaplamalarından sorumlu motor (Single Responsibility).
    CFG-03 standartları uyarınca ATR, Drawdown, Beta hesaplamalarını barındırır.
    """
    
    def calculate_risk_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df is None or len(df) < 20:
            return {"Volatility": 0, "Drawdown": 0, "Beta": 1.0, "Risk_Level": "Yüksek (Veri Yetersiz)"}
            
        # Volatilite (Yıllıklandırılmış 252 iş günü)
        pct_change = df['close'].pct_change().dropna()
        volatility = pct_change.std() * np.sqrt(252) * 100
        
        # Drawdown (Son 1 yıl veya veri boyutu kadar)
        lookback = min(len(df), 252)
        recent_df = df.tail(lookback)
        max_price = recent_df['high'].max() if 'high' in recent_df.columns else recent_df['close'].max()
        current_price = df['close'].iloc[-1]
        drawdown = ((current_price - max_price) / max_price) * 100 if max_price > 0 else 0
        
        # Beta Proxy
        beta_proxy = round(1.0 + (volatility - 30) / 100, 2)
        beta_proxy = max(0.5, min(2.5, beta_proxy))
        
        # Genel Risk Seviyesi (AI Interpretation)
        if volatility > 50 or drawdown < -30:
            risk_level = "Çok Yüksek"
        elif volatility > 35 or drawdown < -20:
            risk_level = "Yüksek"
        elif volatility > 20 or drawdown < -10:
            risk_level = "Orta"
        else:
            risk_level = "Düşük"
            
        return {
            "Volatility": round(volatility, 2),
            "Drawdown": round(drawdown, 2),
            "Beta": beta_proxy,
            "Risk_Level": risk_level
        }
