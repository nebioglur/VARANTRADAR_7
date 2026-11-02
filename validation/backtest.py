import pandas as pd
from typing import Dict, Any

class BacktestValidator:
    """
    CFG-07 Validation Layer (Backtest)
    Sistemin bulduğu işlem kurulumlarının geçmişte çalışıp çalışmadığını test eder.
    Gerçek DataFrame verisi üzerinde vektörel olarak geriye dönük arama yapar.
    """
    
    @staticmethod
    def run_historical_test(symbol: str, df: pd.DataFrame, entry_price: float, stop_loss: float, target_price: float) -> Dict[str, Any]:
        """
        Geçmiş 6 aydaki hareketlere bakarak bu volatilitedeki TP ve Stop hedeflerine
        ulaşma oranını hesaplar.
        """
        if df is None or len(df) < 20:
            return {
                "Symbol": symbol,
                "Total_Historical_Cases": 0,
                "Hit_Rate_Pct": None,
                "Average_Days_to_Target": 0,
                "Status": "REJECTED",
                "Verdict": "Yetersiz Veri"
            }
            
        # Gerçek vektörel Backtest (Geçmiş 6 aydaki her gün için)
        # Eğer geçmişteki bir günün kapanış fiyatı referans alınırsa,
        # kaç gün içinde TP seviyesi büyüklüğünde bir artış veya SL seviyesinde düşüş yaşanıyor?
        
        tp_percent = (target_price - entry_price) / entry_price
        sl_percent = (entry_price - stop_loss) / entry_price
        
        wins = 0
        losses = 0
        ambiguous = 0
        resolved_days = []
        total_cases = max(0, len(df) - 20)
        
        # DataFrame i listeye çevirip hızlı tarama yapalım
        closes = df['close'].tolist()
        highs = df['high'].tolist()
        lows = df['low'].tolist()
        
        for i in range(max(0, len(closes) - 20)): # Keep only origins with a full 20-bar outcome window
            start_price = closes[i]
            target_p = start_price * (1 + tp_percent)
            stop_p = start_price * (1 - sl_percent)
            
            for j in range(i+1, min(i+20, len(closes))): # Max 20 gün bekle
                hit_target = highs[j] >= target_p
                hit_stop = lows[j] <= stop_p
                if hit_target and hit_stop:
                    # OHLC bars cannot reveal event order. Resolve conservatively as a stop.
                    ambiguous += 1
                    losses += 1
                    resolved_days.append(j - i)
                    break
                if hit_stop:
                    losses += 1
                    resolved_days.append(j - i)
                    break
                if hit_target:
                    wins += 1
                    resolved_days.append(j - i)
                    break
                    
        total_trades = wins + losses
        if total_trades == 0:
            hit_rate = None
            avg_days = None
        else:
            hit_rate = (wins / total_trades) * 100.0
            avg_days = sum(resolved_days) / len(resolved_days)
            
        status = "REJECTED"
        if hit_rate is not None and hit_rate > 55.0:
            status = "APPROVED"
            
        return {
            "Symbol": symbol,
            "Total_Historical_Cases": total_cases,
            "Resolved_Trades": total_trades,
            "Ambiguous_Bars_Resolved_As_Stop": ambiguous,
            "Hit_Rate_Pct": round(hit_rate, 1) if hit_rate is not None else None,
            "Average_Days_to_Target": round(avg_days, 2) if avg_days is not None else None,
            "Status": status,
            "Verdict": "Historical OHLC test only; costs, slippage, survivorship and event order may limit validity." if total_trades else "No resolved historical trades; probability unavailable."
        }
