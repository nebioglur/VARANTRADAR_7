from typing import Dict, Any

class PortfolioManager:
    """
    CFG-08 Portfolio Layer
    Tek bir işleme değil, tüm portföyün riskine ve nakit oranına bakar.
    12. (Position Sizing) ve 13. (Likidite/Hedge) altın soruların yanıtlarını üretir.
    """
    
    @staticmethod
    def evaluate_portfolio_impact(symbol: str, market_regime: str, risk_per_trade: float) -> Dict[str, Any]:
        """
        Girdi: Varlık adı, Endeks Rejimi ve o işlem için alınacak risk.
        Çıktı: Sermaye yönetimi ve Hedge tavsiyeleri.
        """
        
        # Gerçek sistemde bu veriler aktif portföy API'sinden (Örn: Binance/BIST bakiyesi) çekilir.
        # Biz burada simüle ediyoruz.
        current_cash_ratio = 40.0 # Portföyün %40'ı nakit
        
        hedge_advice = "Hedge gereksinimi yok."
        if market_regime == "AYI":
            hedge_advice = "DİKKAT: Makro trend (AYI) yönünde olduğu için, bu Long (Alım) pozisyonunun karşılığında VİOP tarafında %50 oranında endeks Short (Hedge) açılması şiddetle önerilir."
        elif market_regime == "YATAY":
            hedge_advice = "Piyasa yönsüz. Beklenmedik kırılımlara karşı pozisyon büyüklüğünü düşük tutun."
            
        liquidity_status = "Tahta derinliği ve likidite güçlü. Kayma (Slippage) riski düşük."
        # Sığ tahtalar (Örn: Alt pazar hisseleri veya hacimsiz varantlar) için bir mock kontrol:
        if len(symbol) > 5: # Varant veya fon ise
            liquidity_status = "Varant/Fon tahtalarında Piyasa Yapıcı makaslarına (Spread) dikkat ediniz. Ani giriş/çıkışlarda ciddi slippage yaşanabilir."
            
        return {
            "Capital_Allocation": {
                "Max_Position_Pct": risk_per_trade,
                "Warning": f"Portföy nakit oranı şu an %{current_cash_ratio}. Alım için yeterli cephane var."
            },
            "Hedging_And_Liquidity": {
                "Liquidity": liquidity_status,
                "Hedge_Advice": hedge_advice
            }
        }
