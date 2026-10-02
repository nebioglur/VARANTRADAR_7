import pandas as pd

class StockComparison:
    """
    VarantRadar Pro V8 - Hisse Karşılaştırma Arenası
    İki veya daha fazla hisseyi teknik, momentum ve risk açısından çarpıştırıp kazananı belirler.
    """
    def __init__(self):
        pass

    def compare_stocks(self, stock1_data: dict, stock2_data: dict) -> dict:
        """Modül 3: İki hissenin Radar Puanlarına göre arenada karşılaşması."""
        
        s1_score = stock1_data.get('Total_Score', 0)
        s2_score = stock2_data.get('Total_Score', 0)
        
        s1_name = stock1_data.get('Symbol', 'Hisse 1')
        s2_name = stock2_data.get('Symbol', 'Hisse 2')
        
        # Basit kazanan mantığı (Puanı yüksek olan)
        if s1_score > s2_score:
            winner = s1_name
            reason = f"{s1_name}, teknik göstergelerde ({s1_score} puan) {s2_name} hissesine ({s2_score} puan) karşı daha güçlü."
        elif s2_score > s1_score:
            winner = s2_name
            reason = f"{s2_name}, teknik göstergelerde ({s2_score} puan) {s1_name} hissesine ({s1_score} puan) karşı daha güçlü."
        else:
            winner = "Berabere"
            reason = "Her iki hissenin teknik gücü eşit."
            
        return {
            "Stock1": s1_name,
            "Stock1_Score": s1_score,
            "Stock2": s2_name,
            "Stock2_Score": s2_score,
            "Winner": winner,
            "Explanation": reason,
            "Radar_Data": {
                s1_name: stock1_data.get('Scores', {}),
                s2_name: stock2_data.get('Scores', {})
            }
        }
