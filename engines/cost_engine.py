from typing import Dict, Any

class CostEngine:
    """
    Portföy işlemlerindeki gizli maliyetleri (Komisyon, Vergi, Spread)
    hesaplayarak 'Brüt Getiri' ile 'Net Getiri' arasındaki farkı çıkarır.
    """
    
    @staticmethod
    def calculate_transaction_costs(trade_value: float, commission_rate: float = 0.001, bsmv_rate: float = 0.05) -> Dict[str, float]:
        """
        trade_value: İşlem hacmi (TL)
        commission_rate: Aracı kurum komisyon oranı (Örn: binde 1 -> 0.001)
        bsmv_rate: Komisyon üzerinden alınan vergi (Örn: %5 -> 0.05)
        """
        if trade_value <= 0:
            return {"total_cost": 0.0, "commission": 0.0, "tax": 0.0}
            
        base_commission = trade_value * commission_rate
        tax_on_commission = base_commission * bsmv_rate
        total_cost = base_commission + tax_on_commission
        
        return {
            "trade_value": round(trade_value, 2),
            "commission": round(base_commission, 2),
            "tax": round(tax_on_commission, 2),
            "total_cost": round(total_cost, 2)
        }

    @staticmethod
    def calculate_net_return(gross_profit: float, holding_days: int, total_transaction_costs: float, tax_on_profit_rate: float = 0.0) -> Dict[str, float]:
        """
        gross_profit: Elde edilen brüt kar (TL)
        holding_days: Pozisyonun elde tutulma süresi
        total_transaction_costs: Alım ve satım sırasında ödenen toplam maliyet
        tax_on_profit_rate: Kar üzerinden alınan stopaj/vergi (Hisselerde genelde 0, Varantlarda 0 veya kurum bazlı değişebilir)
        """
        # Net Kar = Brüt Kar - (İşlem Maliyetleri + Stopaj)
        taxable_profit = max(0, gross_profit - total_transaction_costs)
        profit_tax = taxable_profit * tax_on_profit_rate
        
        net_profit = gross_profit - total_transaction_costs - profit_tax
        
        return {
            "Gross_Profit": round(gross_profit, 2),
            "Total_Costs": round(total_transaction_costs, 2),
            "Profit_Tax": round(profit_tax, 2),
            "Net_Profit": round(net_profit, 2)
        }
        
    @staticmethod
    def target_price_with_costs(entry_price: float, target_net_profit_pct: float = 0.10, commission_rate: float = 0.001) -> float:
        """
        Yatırımcı %10 NET kar istiyorsa, komisyonları (alım + satım)
        düşündüğümüzde hisseyi HANGİ fiyattan satması gerektiğini bulur.
        """
        # Alım maliyeti dahil edilmiş giriş: Entry * (1 + Comm)
        # Hedeflenen Net = Entry * target
        # Satış Maliyeti düşülmüş çıkış: Exit * (1 - Comm)
        # Denklem: Exit * (1 - Comm) - Entry * (1 + Comm) = Entry * target
        # Exit = (Entry * (1 + target + Comm)) / (1 - Comm)
        
        target_exit_price = (entry_price * (1 + target_net_profit_pct + commission_rate)) / (1 - commission_rate)
        return round(target_exit_price, 2)
