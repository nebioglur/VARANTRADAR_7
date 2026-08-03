import pandas as pd
from utils.logger import logger

class StrategyEngine:
    """
    VarantRadar Pro V5 - Profesyonel Strateji Motoru
    Hisse fiyat hareketlerine göre Giriş, Çıkış ve Stop mantığını belirler.
    """
    def __init__(self):
        self.strategies = {
            "SCALP": "Kısa Vade (1-5 Dakika) - Hedef: %1-3",
            "DAY": "Gün İçi İşlem - Hedef: %3-5",
            "SWING": "Orta Vade (3-15 Gün) - Hedef: %10-20",
        }

    def determine_trade_type(self, trend_score: int, volatility: float, rsi: float) -> str:
        """
        Modül 2: Piyasanın durumuna göre işlem türünü belirler.
        """
        if volatility > 0.05 and 40 < rsi < 60:
            return "SCALP"
        elif trend_score > 70:
            return "SWING"
        else:
            return "DAY"

    def calculate_entry_and_stops(self, df_analyzed: pd.DataFrame, action: str, trade_type: str) -> dict:
        """
        Modül 3 & 4: Destek/Direnç veya ATR tabanlı Giriş, Hedef ve İzleyen Stop belirler.
        """
        if df_analyzed.empty:
            return None
            
        latest = df_analyzed.iloc[-1]
        current_price = latest['close']
        atr = latest.get('atr', current_price * 0.02) # Fallback %2 ATR
        
        # Risk Multipliers based on Trade Type
        if trade_type == "SCALP":
            stop_mult, target_mult = 1.0, 1.5
        elif trade_type == "SWING":
            stop_mult, target_mult = 2.0, 3.0
        else: # DAY
            stop_mult, target_mult = 1.5, 2.0

        if action == "AL":
            stop_loss = current_price - (atr * stop_mult)
            target = current_price + (atr * target_mult)
            entry_strategy = "Trend Devamı / Destekten Dönüş" if latest.get('rsi', 50) < 50 else "Direnç Kırılımı (Breakout)"
        else: # SAT
            stop_loss = current_price + (atr * stop_mult)
            target = current_price - (atr * target_mult)
            entry_strategy = "Dirençten Dönüş / Çift Tepe" if latest.get('rsi', 50) > 70 else "Destek Kırılımı (Breakdown)"
            
        return {
            "trade_type": trade_type,
            "entry_price": current_price,
            "stop_loss": round(stop_loss, 2),
            "target": round(target, 2),
            "risk_reward_ratio": round(abs(target - current_price) / abs(current_price - stop_loss), 2) if abs(current_price - stop_loss) > 0 else 0,
            "entry_strategy_note": entry_strategy
        }

    def generate_strategy_report(self, symbol: str, df_analyzed: pd.DataFrame, ai_score: int) -> dict:
        """
        Modül 1 & 11: Nihai İşlem ve Strateji Kararı
        """
        action = "AL" if ai_score >= 50 else "SAT"
        volatility = df_analyzed['close'].pct_change().std() if not df_analyzed.empty else 0.02
        rsi = df_analyzed['rsi'].iloc[-1] if 'rsi' in df_analyzed.columns else 50
        
        trade_type = self.determine_trade_type(ai_score, volatility, rsi)
        plan = self.calculate_entry_and_stops(df_analyzed, action, trade_type)
        
        return {
            "Symbol": symbol,
            "Action": action,
            "Trade_Type": trade_type,
            "Plan": plan,
            "AI_Strategy_Note": f"Sistem {trade_type} stratejisi öneriyor. Hissenin ATR değeri dikkate alınarak giriş stratejisi '{plan['entry_strategy_note']}' olarak belirlendi."
        }
