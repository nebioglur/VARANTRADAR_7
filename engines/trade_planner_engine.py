import pandas as pd
from typing import Dict, Any
import numpy as np

class TradePlannerEngine:
    """
    Sadece işlem planı oluşturmaktan sorumludur (Single Responsibility).
    CFG-01/03 kuralı gereği: Entry, Stop, Target-1, Target-2, ETA, Risk/Reward, Position Size, Probability hesaplar.
    """
    
    def calculate_trade_plan(self, df: pd.DataFrame, total_score: int, risk_level: str) -> Dict[str, Any]:
        if df is None or len(df) < 14:
            return {}
            
        last_row = df.iloc[-1]
        current_price = last_row['close']
        
        # Basit ATR Hesabı (Eğer dataframe'de ATR yoksa proxy)
        if 'ATR' in df.columns:
            atr = df['ATR'].iloc[-1]
        else:
            # Proxy ATR (Son 14 günün True Range ortalaması)
            df['TR'] = np.maximum((df['high'] - df['low']), 
                                  np.maximum(abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift())))
            atr = df['TR'].tail(14).mean() if not df['TR'].isnull().all() else (current_price * 0.02)
            
        # Entry (Giriş): Şu anki fiyattır. Eğer çok yüksek risk ise biraz aşağıya limit emir konulabilir.
        entry_price = current_price
        
        # Stop-Loss: 2 ATR aşağısı
        stop_price = current_price - (2 * atr)
        
        # Target-1: 3 ATR yukarısı
        target_1 = current_price + (3 * atr)
        
        # Target-2: 5 ATR yukarısı
        target_2 = current_price + (5 * atr)
        
        # Risk Reward Ratio
        risk = current_price - stop_price
        reward = target_1 - current_price
        risk_reward_ratio = round(reward / risk, 2) if risk > 0 else 0
        
        # Olasılık (Probability) - Skora dayalı
        probability = min(99, max(10, int(total_score * 0.9)))
        
        # Pozisyon Büyüklüğü Önerisi (Maksimum % risk kuralı)
        # Örnek: Portföyün sadece %2'sini riske atma kuralı
        if risk_level == "Düşük":
            position_size = "%15 - %20"
        elif risk_level == "Orta":
            position_size = "%10 - %15"
        elif risk_level == "Yüksek":
            position_size = "%5 - %10"
        else:
            position_size = "%1 - %5 (Minimum)"
            
        # ETA (Tahmini Süre)
        eta_days = int((target_1 - current_price) / (atr / 2)) if atr > 0 else 5
        eta_days = max(1, min(60, eta_days))
        
        return {
            "Entry": round(entry_price, 2),
            "Stop": round(stop_price, 2),
            "Target_1": round(target_1, 2),
            "Target_2": round(target_2, 2),
            "Risk_Reward": risk_reward_ratio,
            "Probability": f"%{probability}",
            "Position_Size": position_size,
            "ETA_Days": eta_days,
            "ATR": round(atr, 2)
        }
