import pandas as pd
import numpy as np
from typing import Dict, List, Any

from engines.score_engine import ScoreEngine
from engines.risk_engine import RiskEngine
from engines.trade_planner_engine import TradePlannerEngine
from engines.explainable_ai_engine import ExplainableAIEngine

class AIDecisionEngine:
    """
    VarantRadar Pro V4 - AI Karar Motoru (Orchestrator)
    Kural tabanlı bir uzman sistemdir. (Rule-Based Expert System)
    """

    def __init__(self, score_engine=None, risk_engine=None, trade_engine=None, xai_engine=None):
        self.score_engine = score_engine or ScoreEngine()
        self.risk_engine = risk_engine or RiskEngine()
        self.trade_engine = trade_engine or TradePlannerEngine()
        self.xai_engine = xai_engine or ExplainableAIEngine()

    @classmethod
    def generate_ai_report(cls, df: pd.DataFrame, symbol: str, df_4h: pd.DataFrame = None) -> Dict[str, Any]:
        """Sistemi kurumsal yapıya bağlayan ana tetikleyici metod."""
        engine = cls()
        return engine._generate_report(df, symbol, df_4h)

    def _generate_report(self, df: pd.DataFrame, symbol: str, df_4h: pd.DataFrame = None) -> Dict[str, Any]:
        """Tüm V4 AI modüllerini DI (Dependency Injection) kullanarak çalıştırır."""
        if df.empty or len(df) < 20:
            return {"error": "Yetersiz veri"}
            
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # YENİ MİMARİ (CFG-04): Puanlama Motoru (Score Engine)
        score_data = self.score_engine.calculate_scores(df, df_4h)
        total_score = score_data['Total_Score']
        scores = score_data['Details']
        scores['Total'] = total_score # Legacy compatibility
        
        # YENİ MİMARİ (CFG-04): Risk Motoru (Risk Engine)
        risk_metrics = self.risk_engine.calculate_risk_metrics(df)
        
        # YENİ MİMARİ (CFG-04): İşlem Planı (Trade Planner)
        trade_plan = self.trade_engine.calculate_trade_plan(df, total_score, risk_metrics.get('Risk_Level', 'Yüksek'))
        
        # YENİ MİMARİ (CFG-04): Açıklanabilir Yapay Zeka (XAI)
        xai_data = self.xai_engine.generate_explanation(scores, risk_metrics, total_score)
        
        # MODÜL 03: FIRSAT SEVİYESİ
        opportunity_level = AIDecisionEngine._determine_opportunity_level(total_score)
        
        # MODÜL 04: İŞLEM HAZIRLIK DURUMU
        readiness = AIDecisionEngine._determine_readiness(scores, last_row)
        
        # MODÜL 05: ETA MOTORU (Tahmini Varış Süresi)
        eta_days = AIDecisionEngine._calculate_eta(last_row)
        
        # YENİ EKLENEN (P0): Stopa Tahmini Süre
        stop_eta_days = AIDecisionEngine._calculate_time_to_stop(last_row)
        
        # YENİ EKLENEN (P0): Risk / Getiri Oranı
        rr_ratio_val, rr_ratio_str = AIDecisionEngine._calculate_risk_reward(last_row)
        
        # MODÜL 06: BAŞARI OLASILIĞI
        success_prob = AIDecisionEngine._calculate_success_probability(scores, readiness)
        
        # YENİ EKLENEN (P0): İşlem Kalite Puanı
        trade_quality = AIDecisionEngine._calculate_trade_quality(scores, rr_ratio_val, df)
        
        # MODÜL 09: İŞLEM TÜRÜ (Legacy)
        trade_type = AIDecisionEngine._determine_trade_type(last_row, scores)
        
        # CFG-01 MODÜL 03: GÜVEN ARALIĞI (Legacy)
        conf_interval = AIDecisionEngine._calculate_confidence_interval(last_row)
        
        # CFG-01 MODÜL 05: TARİHSEL BENZERLİK (Legacy)
        historical_sim = AIDecisionEngine._find_historical_similarity(df)

        report = {
            "Symbol": symbol,
            "Price": round(last_row['close'], 2),
            "Scores": scores,
            "Total_Score": total_score,
            "Opportunity_Level": opportunity_level,
            "Readiness": readiness,
            "ETA": trade_plan.get('ETA_Days', eta_days),
            "Stop_ETA": stop_eta_days,
            "Risk_Reward": trade_plan.get('Risk_Reward', rr_ratio_str),
            "Trade_Quality": trade_quality,
            "Success_Probability": trade_plan.get('Probability', success_prob),
            "Reasons": xai_data['Reasons'],
            "Missing_Conditions": xai_data['Counter_Opinions'],
            "Trade_Type": trade_type,
            "Scenarios": {
                "En_Iyi": f"Hedef: {trade_plan.get('Target_1')} - {trade_plan.get('Target_2')}",
                "Normal": f"Pozisyon Önerisi: {trade_plan.get('Position_Size')}",
                "Kotu_Stop": f"Zarar Kes (Stop Loss): {trade_plan.get('Stop')}"
            },
            "Confidence_Interval": conf_interval,
            "Historical_Similarity": historical_sim,
            "Risk_Metrics": risk_metrics,
            "Explainable_AI": xai_data,
            "AI_Comment": AIDecisionEngine._generate_summary(opportunity_level, readiness, success_prob)
        }
        return report

    @staticmethod
    def _generate_explainable_ai(scores: Dict[str, float]) -> Dict[str, Any]:
        """
        V6: AI'ın verdiği puanı oluşturan ana bileşenlerin ağırlığını hesaplar.
        """
        total = scores['Total'] if scores['Total'] > 0 else 1
        
        # Orijinal maksimum puanlar: Trend 25, Momentum 20, Vol 15, SR 20, Tech 20
        # Mevcut puanın toplam puana katkı oranları (Yüzde olarak)
        contributions = {
            "Trend": round((scores['Trend'] / total) * 100, 1),
            "Momentum": round((scores['Momentum'] / total) * 100, 1),
            "Hacim": round((scores['Volume'] / total) * 100, 1),
            "Destek_Direnc": round((scores['Support_Resistance'] / total) * 100, 1),
            "Teknik_Uyum": round((scores['Technical'] / total) * 100, 1)
        }
        
        # En etkili olanı bul
        dominant_factor = max(contributions, key=contributions.get)
        
        return {
            "Contributions": contributions,
            "Dominant_Factor": dominant_factor,
            "Explanation": f"Yapay zekanın bu kararı vermesindeki en büyük etken %{contributions[dominant_factor]} ağırlık ile {dominant_factor} oldu."
        }

    @staticmethod
    def _calculate_scores(df: pd.DataFrame, df_4h: pd.DataFrame = None) -> Dict[str, float]:
        last = df.iloc[-1]
        
        # 1. Trend Puanı (Max 25)
        trend_score = 0
        if last['close'] > last.get('EMA', 0): trend_score += 10
        if last['close'] > last.get('SMA', 0): trend_score += 5
        if last.get('ADX', 0) > 25: trend_score += 10
        elif last.get('ADX', 0) > 20: trend_score += 5
        
        # 2. Momentum Puanı (Max 20)
        mom_score = 0
        rsi = last.get('RSI', 50)
        if 40 < rsi < 70: mom_score += 10
        elif rsi >= 70: mom_score += 5 # Overbought ama güçlü
        
        macd_hist = last.get('MACD', 0) - last.get('MACD_Signal', 0)
        if macd_hist > 0: mom_score += 10
        
        # 3. Hacim Puanı (Max 15)
        vol_score = 0
        vol_sma = df['volume'].rolling(20).mean().iloc[-1]
        if last['volume'] > vol_sma * 1.5: vol_score += 15
        elif last['volume'] > vol_sma: vol_score += 10
        elif last['volume'] > vol_sma * 0.8: vol_score += 5
        
        # 4. Destek/Direnç ve Formasyon Puanı (Max 20)
        sr_score = 0
        if last.get('close') > last.get('Pivot', 0): sr_score += 5
        if last.get('Breakout_Up', False): sr_score += 15
        elif last.get('Bullish_Flag_Pennant', False): sr_score += 10
        elif last.get('Double_Bottom', False): sr_score += 10
        elif last.get('TOBO', False): sr_score += 10
        
        # 5. Teknik Uyum (Max 20)
        tech_score = 0
        if last['close'] > last.get('VWAP', 0): tech_score += 10
        if last.get('CCI', 0) > 100: tech_score += 5
        if last.get('MFI', 50) > 50: tech_score += 5
        
        # CFG-02 M02: Multi-Timeframe Uyumu (Maks 20 ekstra puan)
        mtf_score = 0
        if df_4h is not None and not df_4h.empty:
            last_4h = df_4h.iloc[-1]
            if last_4h['close'] > last_4h.get('EMA', 0): mtf_score += 10
            if last_4h.get('MACD', 0) > last_4h.get('MACD_Signal', 0): mtf_score += 10
        
        total = trend_score + mom_score + vol_score + sr_score + tech_score + mtf_score
        
        return {
            "Trend": trend_score,
            "Momentum": mom_score,
            "Volume": vol_score,
            "Support_Resistance": sr_score,
            "Technical": tech_score,
            "Multi_Timeframe": mtf_score,
            "Total": min(100, max(0, total))
        }

    @staticmethod
    def _determine_opportunity_level(score: float) -> str:
        if score >= 90: return "S Seviye (Mükemmel)"
        elif score >= 80: return "A Seviye (Çok İyi)"
        elif score >= 70: return "B Seviye (İyi)"
        elif score >= 60: return "C Seviye (Orta)"
        elif score >= 50: return "D Seviye (Zayıf)"
        elif score >= 30: return "E Seviye (Riskli)"
        else: return "F Seviye (Uzak Dur)"

    @staticmethod
    def _determine_readiness(scores: Dict[str, float], last_row: pd.Series) -> str:
        if scores['Total'] >= 80 and scores['Volume'] >= 10:
            return "Hazır"
        elif scores['Total'] >= 70:
            return "Hazırlanıyor"
        elif scores['Total'] >= 60:
            return "Takip Et"
        elif scores['Total'] >= 40:
            return "Beklemede"
        else:
            return "Pas Geç"

    @staticmethod
    def _calculate_eta(last_row: pd.Series) -> str:
        atr = last_row.get('ATR', last_row['close'] * 0.02)
        if atr == 0: return "Belirsiz"
        
        # Basit bir R2 (Direnç) hedefine ulaşma süresi
        dist_to_r1 = abs(last_row.get('R1', last_row['close'] * 1.05) - last_row['close'])
        days_needed = dist_to_r1 / atr
        
        if days_needed <= 1: return "Bugün / 1 Gün"
        elif days_needed <= 3: return "2-3 Gün"
        elif days_needed <= 5: return "1 Hafta"
        elif days_needed <= 10: return "2 Hafta"
        else: return "1 Ay+"

    @staticmethod
    def _calculate_time_to_stop(last_row: pd.Series) -> str:
        atr = last_row.get('ATR', last_row['close'] * 0.02)
        if atr == 0: return "Belirsiz"
        
        # Stop mesafesi S1 veya manuel hesaplanabilir
        dist_to_s1 = abs(last_row['close'] - last_row.get('S1', last_row['close'] * 0.95))
        days_needed = dist_to_s1 / atr
        
        if days_needed <= 1: return "1 Günden Az (Yüksek Risk)"
        elif days_needed <= 3: return "1-3 Gün"
        elif days_needed <= 5: return "3-5 Gün (Normal)"
        else: return "Güvenli Uzaklıkta"

    @staticmethod
    def _calculate_risk_reward(last_row: pd.Series) -> tuple:
        price = last_row['close']
        r1 = last_row.get('R1', price * 1.05)
        s1 = last_row.get('S1', price * 0.95)
        
        reward = abs(r1 - price)
        risk = abs(price - s1)
        
        if risk == 0: return 0.0, "Tanımsız"
        
        rr_ratio = reward / risk
        return round(rr_ratio, 2), f"1:{round(rr_ratio, 1)}"

    @staticmethod
    def _calculate_trade_quality(scores: Dict[str, float], rr_ratio: float, df: pd.DataFrame) -> int:
        quality = 0
        # Hacim destekliyor mu? (Max 40)
        vol_score = scores['Volume']
        quality += (vol_score / 15) * 40
        
        # Risk/Reward 1:2'den büyük mü? (Max 30)
        if rr_ratio >= 2.0: quality += 30
        elif rr_ratio >= 1.5: quality += 20
        elif rr_ratio >= 1.0: quality += 10
        
        # Son 5 mumda volatilite (Max 30)
        last = df.iloc[-1]
        atr_pct = last.get('ATR', 0) / last['close'] * 100
        if atr_pct < 2: quality += 30
        elif atr_pct < 4: quality += 15
        
        return int(min(100, max(0, quality)))

    @staticmethod
    def _calculate_success_probability(scores: Dict[str, float], readiness: str) -> str:
        base_prob = scores['Total']
        # Hacim destekliyse başarı olasılığı artar
        if readiness == "Hazır":
            base_prob = min(95, base_prob + 5)
        elif readiness == "Pas Geç":
            base_prob = max(10, base_prob - 20)
            
        return f"%{int(base_prob)}"

    @staticmethod
    def _generate_reasons(df: pd.DataFrame, scores: Dict[str, float]) -> tuple:
        last = df.iloc[-1]
        reasons = []
        missing = []
        
        if scores['Trend'] >= 20: reasons.append("Trend çok güçlü (EMA, SMA ve ADX pozitif).")
        else: missing.append("Güçlü bir yükseliş trendi teyidi yok.")
        
        if scores['Volume'] >= 10: reasons.append("Hacim ortalamanın üzerinde, alıcı iştahı yüksek.")
        else: missing.append("Hacim desteği zayıf, kırılımlar sahte (fakeout) olabilir.")
        
        if scores['Momentum'] >= 15: reasons.append("Momentum göstergeleri (RSI/MACD) alım yönünde destekliyor.")
        else: missing.append("RSI veya MACD henüz net bir alım sinyali/onayı üretmedi.")
        
        if last.get('Breakout_Up', False): reasons.append("Yakın direnç kırıldı (Breakout).")
        
        if len(reasons) == 0: reasons.append("Şu an için pozitif bir teknik gerekçe bulunamadı.")
        if len(missing) == 0: missing.append("Tüm ana teknik şartlar sağlanmış durumda.")
        
        return reasons, missing

    @staticmethod
    def _determine_trade_type(last_row: pd.Series, scores: Dict[str, float]) -> str:
        adx = last_row.get('ADX', 20)
        atr_pct = last_row.get('ATR', 0) / last_row['close'] * 100
        
        if atr_pct > 4: return "Scalping / Gün İçi (Yüksek Volatilite)"
        elif adx > 25 and scores['Total'] >= 70: return "Swing (Kısa-Orta Vade Trend Takibi)"
        else: return "Bekle / Yatay Piyasada İşlem Yapma"

    @staticmethod
    def _generate_scenarios(df: pd.DataFrame, last_row: pd.Series) -> Dict[str, str]:
        r1 = round(last_row.get('R1', last_row['close'] * 1.05), 2)
        s1 = round(last_row.get('S1', last_row['close'] * 0.95), 2)
        
        return {
            "En_Iyi": f"Hacimli alımların devamı halinde fiyatın ivmelenerek {r1} direncini kırması ve yeni zirveler test etmesi beklenir.",
            "Normal": f"Fiyatın kısa vadede {s1} ile {r1} arasında konsolide olması ve güç toplaması muhtemeldir.",
            "Kotu_Stop": f"Ani satış baskısı gelirse veya endeks bozulursa fiyatın {s1} desteğini kırarak alt kanala inme riski vardır. {s1} altı stop loss (zarar kes) bölgesidir."
        }

    @staticmethod
    def _calculate_confidence_interval(last_row: pd.Series) -> str:
        price = last_row['close']
        atr = last_row.get('ATR', price * 0.02)
        # %95 Güven Aralığı tahmini (yaklaşık 1.96 ATR)
        upper = price + (1.96 * atr)
        lower = max(0.01, price - (1.96 * atr))
        return f"{lower:.2f} ₺ - {upper:.2f} ₺"

    @staticmethod
    def _find_historical_similarity(df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < 50:
            return {"Similar_Date": "Yetersiz Veri", "Similarity_Score": 0, "Outcome": "Belirsiz"}
            
        current_pattern = df['close'].tail(14).values
        if len(current_pattern) < 14:
            return {"Similar_Date": "Yetersiz Veri", "Similarity_Score": 0, "Outcome": "Belirsiz"}
            
        current_pct = pd.Series(current_pattern).pct_change().fillna(0).values
        
        best_score = -1
        best_idx = 0
        
        closes = df['close'].values
        pct_changes = df['close'].pct_change().fillna(0).values
        
        # Son 30 günü arama dışı bırak
        for i in range(14, len(closes) - 30):
            window = pct_changes[i-14:i]
            # Sıfıra bölme hatasını önlemek için standart sapmayı kontrol et
            if np.std(current_pct) == 0 or np.std(window) == 0:
                continue
            corr = np.corrcoef(current_pct, window)[0, 1]
            if not np.isnan(corr) and corr > best_score:
                best_score = corr
                best_idx = i
                
        if best_score > 0.75:
            # 5 gün sonraki değişim
            future_return = (closes[best_idx + 5] - closes[best_idx]) / closes[best_idx] * 100
            date_str = str(df['date'].iloc[best_idx]).split(' ')[0]
            outcome = f"%{abs(future_return):.2f} " + ("Yükseldi" if future_return > 0 else "Düştü")
            return {
                "Similar_Date": date_str,
                "Similarity_Score": round(best_score * 100, 1),
                "Outcome": outcome
            }
        else:
            return {"Similar_Date": "Eşleşme Bulunamadı", "Similarity_Score": 0, "Outcome": "Belirsiz"}

    @staticmethod
    def _calculate_risk_metrics(df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < 20:
            return {"Volatility": 0, "Drawdown": 0, "Beta": 1.0}
            
        # Volatilite (Yıllıklandırılmış 252 iş günü)
        pct_change = df['close'].pct_change().dropna()
        volatility = pct_change.std() * np.sqrt(252) * 100
        
        # Drawdown (Son 1 yıl veya veri boyutu kadar)
        lookback = min(len(df), 252)
        recent_df = df.tail(lookback)
        max_price = recent_df['high'].max() if 'high' in recent_df.columns else recent_df['close'].max()
        current_price = df['close'].iloc[-1]
        drawdown = ((current_price - max_price) / max_price) * 100
        
        # Beta Proxy (Endeks verisi olmadan kaba tahmin: Kendi MA200'üne göre sapma)
        # CFG-03 Notu: Gerçek BIST100 betası için Scanner'a XU100 eklenmelidir. Şimdilik proxy hesaplanır.
        beta_proxy = round(1.0 + (volatility - 30) / 100, 2)
        beta_proxy = max(0.5, min(2.5, beta_proxy))
        
        # Varant Proxy Greeks (Matematiksel Varsayım - Black Scholes)
        # CFG-03 Notu: Türkiye Varant Piyasasında anlık grekler kapalıdır.
        
        return {
            "Volatility": round(volatility, 2),
            "Drawdown": round(drawdown, 2),
            "Beta": beta_proxy,
            "Greeks_Proxy": {
                "Delta": "Canlı Veri Yok",
                "Theta": "Zaman Değeri",
                "Gamma": "Korunuyor"
            }
        }

    @staticmethod
    def _generate_summary(opp: str, readi: str, prob: str) -> str:
        if readi in ["Hazır", "Hazırlanıyor"]:
            return f"Sistem bu hissede {opp} seviyesinde bir fırsat görüyor. Başarı ihtimali {prob} olarak hesaplandı. İşlem planına sadık kalınarak değerlendirilebilir."
        else:
            return f"Fırsat seviyesi şu an {opp}. Riskler yüksek olduğu için sistem {readi} kararı verdi. Acele edilmemeli."
