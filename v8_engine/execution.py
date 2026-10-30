from typing import Dict, Any

class ExecutionEngine:
    """
    V8 Execution & Avoid Engine
    İyi bir hisse bulunsa bile "Şu an girilir mi?" sorusunu yanıtlar.
    Artık kırılımın zaman çerçevesi (hız/momentum) ve çoklu periyot uyumuna
    göre karar verir.
    """
    def __init__(self):
        pass
        
    def evaluate_entry(self, breakout_data: Dict[str, Any], market_regime: str) -> Dict[str, Any]:
        """
        Breakout Engine'den gelen verilere göre giriş kararı verir.
        """
        if not breakout_data or not breakout_data.get("is_breakout"):
            return self._default_result("NO_SIGNAL")

        symbol = breakout_data.get("symbol")
        b_score = breakout_data.get("breakout_score", 0)
        f_risk = breakout_data.get("fakeout_risk", 0)
        metrics = breakout_data.get("metrics", {})
        rsi = metrics.get("rsi", 50)
        rel_vol = metrics.get("relative_volume", 1.0)
        
        status = "NO_ENTRY"
        reasons = []
        timeframe_quality = 0
        
        # 1. Temel Ret Kriterleri (Avoid Engine)
        if f_risk >= 50:
            reasons.append("Yüksek tuzak riski (%50 üzeri)")
            return self._build_result(symbol, "NO_ENTRY", reasons, "HIGH_RISK", timeframe_quality)

        # 1b. REJIM KILIDI: canli islem istatistigi, girislerin %62'sinin AYI
        # rejiminde acildigini ve bu grupta kazanma oraninin cok dustugunu
        # gosterdi. Ayi piyasalarinda kirilim sinyalleri tamamen kilitlenir;
        # istisna yok. (Kullanici guvenligi icin sert kural.)
        if market_regime in ["BEAR", "STRONG_BEAR"]:
            reasons.append("Piyasa AYI rejiminde; kırılım girişleri kilitli (istatistik: ayı piyasasında giriş başarısı çok düşük)")
            return self._build_result(symbol, "NO_ENTRY", reasons, "MARKET_REGIME_LOCK", timeframe_quality)
        # NÖTR rejimdeki iki yıllık örneklem başabaşın altında kaldı.
        # Bu rejimde sermaye korunur; yalnızca piyasa yeniden BOĞA'ya
        # döndüğünde yeni giriş açılır.
        if market_regime == "NEUTRAL":
            reasons.append("Piyasa NÖTR; doğrulanmış trend oluşana kadar nakit korunuyor")
            return self._build_result(symbol, "NO_ENTRY", reasons, "NEUTRAL_PRESERVE_CASH", timeframe_quality)
        
        # 2. Zaman Çerçevesi / Momentum Hızı Analizi
        # Hacim ve RSI'ye göre kırılımın "hızını" sınıflandırır
        speed = "NORMAL"
        if rel_vol > 2.0 and 55 <= rsi <= 70:
            speed = "EXPLOSIVE"
            timeframe_quality += 30
        elif rel_vol > 1.5 and 50 <= rsi <= 75:
            speed = "STRONG"
            timeframe_quality += 20
        elif rel_vol >= 1.0:
            speed = "NORMAL"
            timeframe_quality += 10
        else:
            speed = "WEAK"
            reasons.append("Bu kırılım için hacim hızı zayıf")
        
        # 3. Aşırı Uzama / Kovalama Riski (Chase Risk)
        if rsi > 80:
            status = "CHASE_RISK"
            reasons.append(f"Fiyat aşırı alımda (RSI: {rsi}); kovalamayın")
            timeframe_quality -= 15
            
        # 4. Pullback Bekleme
        elif rsi > 70 and b_score < 60:
            status = "WAIT_PULLBACK"
            reasons.append("Momentum yüksek ancak kırılım mutlak güçte değil; düzeltme (retest) beklenmeli")
            timeframe_quality -= 5
            
        # 5. Temiz Giriş (Enter)
        # Rejime gore dinamik giris barasi: backtest kaniti — NÖTR gunde
        # kirilim kenari kayboluyor (WR %39.5, PF 1.05), bu yuzden NÖTR'de
        # sadece en guclu kirilimlar girsin. BOGA'da baraj temel seviyede.
        if market_regime == "NEUTRAL":
            b_score_min, f_risk_max = 62, 32
        elif market_regime == "STRONG_BULL":
            b_score_min, f_risk_max = 45, 42
        else:
            b_score_min, f_risk_max = 50, 40
        if b_score >= b_score_min and f_risk <= f_risk_max:
            status = "ENTER"
            if market_regime == "NEUTRAL":
                reasons.append("Nötr piyasada yüksek barajı geçen güçlü kırılım (AL)")
            else:
                reasons.append("Düşük tuzak riskli, güçlü kırılım onayı (AL)")
        elif b_score >= 35:
            status = "WAIT_CONFIRMATION"
            reasons.append("Kırılım başladı; hacim/zaman teyidi bekleniyor")
        else:
            status = "NO_ENTRY"
            reasons.append("Kırılım gücü zayıf, izleniyor")
        
        timeframe_quality = max(0, min(100, timeframe_quality + b_score * 0.5 - f_risk * 0.3))
        
        return self._build_result(symbol, status, reasons, "OK", round(timeframe_quality, 1), speed)
        
    def _build_result(self, symbol, status, reasons, risk_level, timeframe_quality=0.0, speed="NORMAL"):
        return {
            "symbol": symbol,
            "entry_status": status,
            "reasons": reasons,
            "risk_profile": risk_level,
            "timeframe_quality": timeframe_quality,
            "momentum_speed": speed
        }
        
    def _default_result(self, reason):
        return {
            "symbol": "UNKNOWN",
            "entry_status": "NO_ENTRY",
            "reasons": [reason],
            "risk_profile": "UNKNOWN",
            "timeframe_quality": 0.0,
            "momentum_speed": "-"
        }
