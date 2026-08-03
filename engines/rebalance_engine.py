import pandas as pd
from typing import Dict, Any, List

class RebalanceEngine:
    """
    Portföy ağırlıklarını hedef ağırlıklarla (Target Weights) karşılaştırıp
    alım-satım (dengeleme) önerileri sunar.
    """
    
    @staticmethod
    def calculate_rebalance(current_portfolio: pd.DataFrame, target_weights: Dict[str, float], total_capital: float) -> pd.DataFrame:
        """
        current_portfolio DF beklentisi: ['symbol', 'current_price', 'quantity']
        target_weights: {'ASELS.IS': 0.40, 'THYAO.IS': 0.30, 'CASH': 0.30} vs
        """
        if current_portfolio.empty:
            # Sadece alım önerileri oluştur
            data = []
            for sym, weight in target_weights.items():
                if sym != 'CASH':
                    target_val = total_capital * weight
                    data.append({
                        "symbol": sym,
                        "current_weight": 0.0,
                        "target_weight": weight,
                        "current_value": 0.0,
                        "target_value": target_val,
                        "difference": target_val,
                        "action": "BUY"
                    })
            return pd.DataFrame(data)
            
        current_portfolio['current_value'] = current_portfolio['current_price'] * current_portfolio['quantity']
        current_total = current_portfolio['current_value'].sum()
        # Eğer total_capital daha büyükse nakit var demektir, ona göre hesaplıyoruz.
        working_capital = max(current_total, total_capital)
        
        rebalance_data = []
        for sym, target_w in target_weights.items():
            if sym == 'CASH':
                continue
                
            row = current_portfolio[current_portfolio['symbol'] == sym]
            current_val = row['current_value'].iloc[0] if not row.empty else 0.0
            
            target_val = working_capital * target_w
            diff = target_val - current_val
            
            action = "HOLD"
            if diff > (working_capital * 0.01): # %1 threshold
                action = "BUY"
            elif diff < -(working_capital * 0.01):
                action = "SELL"
                
            rebalance_data.append({
                "symbol": sym,
                "current_weight": current_val / working_capital,
                "target_weight": target_w,
                "current_value": current_val,
                "target_value": target_val,
                "difference": diff,
                "action": action
            })
            
        # Hedefte olmayan ama elde olanları sat
        for idx, row in current_portfolio.iterrows():
            sym = row['symbol']
            if sym not in target_weights:
                rebalance_data.append({
                    "symbol": sym,
                    "current_weight": row['current_value'] / working_capital,
                    "target_weight": 0.0,
                    "current_value": row['current_value'],
                    "target_value": 0.0,
                    "difference": -row['current_value'],
                    "action": "SELL"
                })
                
        return pd.DataFrame(rebalance_data)
