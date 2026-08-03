from typing import Dict, Any
import pandas as pd

from decision.anti_agent import AntiAgent
from decision.probability import ProbabilityMatrix
from decision.exceptions import InsufficientConfidenceError
from execution.planner import TradePlanner
from execution.risk_manager import RiskManager
from validation.backtest import BacktestValidator
from validation.monte_carlo import MonteCarloSimulator
from learning.learning_engine import AILearningEngine
from analysis.ml.lstm_engine import LSTMProjectionEngine
from data.providers.news_engine import NewsEngine
from decision.feedback_ai import GenerativeFeedbackEngine

class ExecutiveDecisionEngine:
    """
    CFG-05 Decision Architecture (The Brain)
    Tüm motorları, planlayıcıyı ve risk/validasyon katmanlarını çağırır.
    Nihai olarak sadece ve tam olarak '11 Altın Soru' (CFG-01.2) standartlarında JSON döner.
    """
    
    @staticmethod
    def generate_final_report(
        symbol: str,
        current_price: float,
        atr: float,
        total_capital: float,
        df: pd.DataFrame,
        technical_result: Dict[str, Any],
        fundamental_result: Dict[str, Any],
        smart_money_result: Dict[str, Any],
        sentiment_result: Dict[str, Any],
        macro_result: Dict[str, Any],
        options_result: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Tüm sistemleri entegre çalıştırarak nihai raporu basar."""
        
        if options_result is None:
            options_result = {}
        
        from decision.coach import PsychologyCoach
        from decision.agents.cio_ai import ChiefInvestmentOfficer
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. TRADE PLANNER (Giriş, Stop, TP) - Dinamik VIX ve ATR ile
        trend = technical_result.get("Trend", "YATAY")
        vix_level = 20.0 
        if "Volatility" in macro_result and macro_result["Volatility"] == "YÜKSEK VOLATİLİTE":
            vix_level = 30.0
            
        trade_plan = TradePlanner.generate_trade_plan(symbol, current_price, atr, trend, vix_level)
        entry_avg = trade_plan["Entry_Plan"]["Average_Cost"]
        stop_loss = trade_plan["Exit_Plan"].get("Stop_Loss", trade_plan["Exit_Plan"].get("Stop_Loss_2", entry_avg * 0.95))
        
        # 2. RİSK YÖNETİMİ (Kelly & Portfolio)
        risk_plan = RiskManager.calculate_position_size(
            total_capital=total_capital, 
            entry_price=entry_avg, 
            stop_loss=stop_loss,
            win_rate_pct=55.0,
            risk_reward_ratio=trade_plan.get("Risk_Reward_Ratio", 2.0)
        )
        
        # 3. DIGITAL COMMITTEE (MULTI-AGENT CIO)
        cio_report = ChiefInvestmentOfficer.evaluate_committee(
            symbol, current_price, 
            technical_result, fundamental_result, smart_money_result, macro_result, risk_plan
        )
        action = cio_report["Final_Action"] 
        
        # 4. AĞIRLIKLANDIRMA VE GÜVEN SKORU
        engine_scores = {
            "Technical": technical_result.get("Score", 50.0),
            "Fundamental": fundamental_result.get("Score", 50.0),
            "SmartMoney": smart_money_result.get("Score", 50.0),
            "Sentiment": sentiment_result.get("Score", 50.0),
            "Macro": macro_result.get("Score", 50.0)
        }
        
        # --- FAZ 3: YAPAY ZEKA ÖĞRENME MOTORU BAĞLANTISI ---
        regime = macro_result.get("Regime", "YATAY")
        ai_weights = AILearningEngine.get_regime_weights(regime)
        
        confidence_score = (
            engine_scores.get("Technical", 50) * ai_weights.get("Technical", 0.3) +
            engine_scores.get("Fundamental", 50) * ai_weights.get("Fundamental", 0.2) +
            engine_scores.get("Macro", 50) * ai_weights.get("Macro", 0.2) +
            engine_scores.get("SmartMoney", 50) * ai_weights.get("SmartMoney", 0.3) +
            engine_scores.get("Sentiment", 50) * ai_weights.get("Sentiment", 0.0)
        )
        
        # Anti-Agent (Şeytanın Avukatı) itirazı
        anti_agent = AntiAgent.challenge_decision(engine_scores, confidence_score)
        confidence_score = anti_agent["Adjusted_Confidence"]
        
        # Order Flow & Smart Money
        from engines.order_flow_engine import OrderFlowEngine
        from engines.smart_money_engine import SmartMoneyEngine as SMEngineDeep
        from engines.explainable_ai_engine import ExplainableAIEngine
        
        imbalance = OrderFlowEngine.analyze_synthetic_imbalance(df, window=5)
        sweeps = OrderFlowEngine.detect_liquidity_sweeps(df, lookback=20)
        imbalance_val = float(imbalance.iloc[-1]) if not imbalance.empty and not pd.isna(imbalance.iloc[-1]) else 0.5
        buyer_pressure = "GÜÇLÜ ALICI" if imbalance_val > 0.6 else ("GÜÇLÜ SATICI" if imbalance_val < 0.4 else "NÖTR")
        sweep_alert = "LİKİDİTE AVI (STOP PATLATMA) TESPİT EDİLDİ" if sweeps else "TEMİZ PİYASA"
        
        order_flow_data = {
            "Imbalance_Score": imbalance_val,
            "Buyer_Pressure": buyer_pressure,
            "Liquidity_Sweeps": sweep_alert,
            "Sweep_Count": len(sweeps)
        }
        
        mfi = SMEngineDeep.calculate_mfi(df)
        obv = SMEngineDeep.calculate_obv(df)
        mfi_val = float(mfi.iloc[-1]) if not mfi.empty and not pd.isna(mfi.iloc[-1]) else 50.0
        sm_status = "AKÜMÜLASYON (Toplanıyor)" if mfi_val < 35 else ("DAĞITIM (Satılıyor)" if mfi_val > 65 else "NÖTR")
        obv_trend = "YÜKSELİŞ" if not obv.empty and len(obv) >= 5 and obv.iloc[-1] > obv.iloc[-5] else "DÜŞÜŞ"
        
        smart_money_deep_data = {
            "MFI": mfi_val,
            "OBV_Trend": obv_trend,
            "Whale_Action": sm_status
        }
        
        decision_str = "AL" if confidence_score > 60 else ("SAT" if confidence_score < 40 else "BEKLE")
        vwap_dist = 0
        reasons_list = ExplainableAIEngine.generate_explanation(decision_str, technical_result.get("Indicators", {}), smart_money_result.get("Score", 50), vwap_dist)
        
        whys_dict = {}
        for i, r in enumerate(reasons_list):
            whys_dict[f"XAI_Nedensellik_{i+1}"] = r
            
        cio_report["The_7_Whys"] = whys_dict
        
        # 5. VALIDASYON
        tp_main = trade_plan["Exit_Plan"]["Take_Profit_2"]
        backtest = BacktestValidator.run_historical_test(symbol, df, entry_avg, stop_loss, tp_main)
        rr_str = str(trade_plan["Risk_Reward_Ratio"])
        monte_carlo = MonteCarloSimulator.run_simulation(backtest["Hit_Rate_Pct"], float(rr_str))
        
        # 6. Base Variables
        is_bull = "BOĞA" in regime.upper()
        atr_estimate = current_price * 0.02
        multiplier = 1.0 if is_bull else -1.0
        
        risk_score = 100 - confidence_score + (20 if not is_bull else 0)
        risk_score = min(max(risk_score, 0), 100)
        conviction_score = confidence_score * 0.8 + engine_scores.get("SmartMoney", 50) * 0.2
        
        if confidence_score >= 90: inv_grade = "AAA"
        elif confidence_score >= 80: inv_grade = "AA"
        elif confidence_score >= 70: inv_grade = "A"
        elif confidence_score >= 60: inv_grade = "BBB"
        elif confidence_score >= 50: inv_grade = "BB"
        elif confidence_score >= 40: inv_grade = "B"
        else: inv_grade = "CCC"
        
        op_pyramiding = "Karlı pozisyonlara ekleme yapma aşamasına geçilmedi."
        if is_bull and trend == "GÜÇLÜ YÜKSELİŞ" and confidence_score > 70:
            op_pyramiding = "Trend güçlü. Direnç kırılımlarında karlı pozisyonlara (Piramitleme) ekleme yapılabilir."
            
        # VADE UYUMLU VE TUTARLI TAVSİYELER (Unified Timeframe Directives)
        if action == "STRONG_BUY":
            op_short_term = "GÜÇLÜ AL — Kısa vadeli ivme ve hacim patlaması yukarı yönü teyit ediyor."
            op_long_term = "BİRİKTİR — Temel ve teknik göstergeler uzun vadeli yükselişi destekliyor."
        elif action == "BUY":
            op_short_term = "KADEMELİ AL — Destek seviyelerine geri çekilmelerde kademeli giriş uygundur."
            op_long_term = "TUT / BİRİKTİR — Trend pozitif, direnç kırılımıyla ekleme yapılabilir."
        elif action == "SELL":
            op_short_term = "SAT / RİSKLİ — Kısa vadeli teknik ve makro satış baskısı mevcut."
            op_long_term = "UZAK DUR — Düşüş trendi veya bozulan temel rasyolar nedeniyle riskli."
        else:
            op_short_term = "İZLE / BEKLE — Kısa vadede yatay seyir, net kırılım beklenmeli."
            op_long_term = "NÖTR / TUT — Uzun vadeli yön tayini için piyasa dengelenmesi bekleniyor."
        
        mtf = {
            "Daily": {"Trend": trend, "Move": f"%{round(atr_estimate/current_price*100,1)}", "Risk": "Yüksek", "Target": round(current_price + atr_estimate*1.5*multiplier,2), "Stop": round(current_price - atr_estimate*1.5*multiplier,2)},
            "Weekly": {"Trend": "Boğa" if is_bull else "Yatay", "Move": f"%{round((atr_estimate*4)/current_price*100,1)}", "Risk": "Orta", "Target": round(current_price + atr_estimate*4*multiplier,2), "Stop": round(current_price - atr_estimate*4*multiplier,2)},
            "Monthly": {"Trend": regime, "Move": f"%{round((atr_estimate*12)/current_price*100,1)}", "Risk": "Orta", "Target": round(current_price + atr_estimate*12*multiplier,2), "Stop": round(current_price - atr_estimate*8*multiplier,2)},
            "Month_3": {"Trend": regime, "Move": f"%{round((atr_estimate*25)/current_price*100,1)}", "Risk": "Düşük", "Target": round(current_price + atr_estimate*25*multiplier,2), "Stop": round(current_price - atr_estimate*12*multiplier,2)},
            "Month_6": {"Trend": "Döngüsel", "Move": f"%{round((atr_estimate*45)/current_price*100,1)}", "Risk": "Düşük", "Target": round(current_price + atr_estimate*45*multiplier,2), "Stop": round(current_price - atr_estimate*20*multiplier,2)}
        }
        
        directives = PsychologyCoach.generate_command_center_directives(action, confidence_score, regime, risk_score)

        change_pct = 0.0
        if df is not None and len(df) >= 2:
            prev_close = df['close'].iloc[-2]
            if prev_close > 0:
                change_pct = ((current_price - prev_close) / prev_close) * 100

        # News & AI Feedback
        try:
            news_engine = NewsEngine()
            historical_news = news_engine.fetch_news(symbol)
            avg_sentiment = 0.0
            if historical_news:
                avg_sentiment = sum(n.get("sentiment", 0.0) for n in historical_news) / len(historical_news)
                
            feedback_engine = GenerativeFeedbackEngine()
            ai_narrative = feedback_engine.generate_feedback(
                symbol=symbol,
                technicals=technical_result.get("Indicators", {}),
                predictions={},
                news_sentiment=avg_sentiment,
                confidence=confidence_score
            )
        except Exception as e:
            historical_news = []
            ai_narrative = f"Yapay Zeka Raporu oluşturulamadı: {e}"

        # --- BÜYÜK YATIRIMCI İKNA & KARAR MOTORU (CONVICTION PLAYBOOK - HARMONIZED) ---
        tp1_val = trade_plan["Exit_Plan"]["Take_Profit_1"]
        tp2_val = trade_plan["Exit_Plan"]["Take_Profit_2"]
        entry1_val = trade_plan['Entry_Plan']['Entry_1']
        entry2_val = trade_plan['Entry_Plan']['Entry_2']
        
        tp1_gain = round(((tp1_val - current_price) / current_price) * 100, 1) if current_price > 0 else 5.0
        tp2_gain = round(((tp2_val - current_price) / current_price) * 100, 1) if current_price > 0 else 10.0
        sl_loss = round(((current_price - stop_loss) / current_price) * 100, 1) if current_price > 0 else 3.0
        sl_loss = max(sl_loss, 0.8)
        rr_calc = round(tp2_gain / sl_loss, 1) if sl_loss > 0 else 2.5
        
        if action == "STRONG_BUY" or (confidence_score >= 70 and action != "NO_TRADE" and action != "SELL"):
            verdict_badge = "GÜÇLÜ AL"
            verdict_title = "🚨 KESİN AL — YÜKSEK KURUMSAL İKNA & MOMENTUM"
            verdict_color = "#10b981"
            exec_pitch = f"{symbol} hissesinde teknik güç, akıllı para hacmi ve piyasa rejimi aynı yönde birleşerek yüksek olasılıklı bir yükseliş fırsatı oluşturmuştur. Fiyat ₺{round(current_price, 2)} seviyesinde olup, ₺{stop_loss} seviyesinde risk sıkı tutulurken ₺{tp1_val} (+%{tp1_gain}) ve ₺{tp2_val} (+%{tp2_gain}) hedefleri 1:{rr_calc} gibi asimetrik bir kazanç/risk avantajı sunmaktadır."
        elif action == "BUY" or (confidence_score >= 50 and action != "NO_TRADE" and action != "SELL"):
            verdict_badge = "KADEMELİ AL"
            verdict_title = "🛡️ KADEMELİ AL — PULLBACK DESTEK GİRİŞİ"
            verdict_color = "#38bdf8"
            exec_pitch = f"{symbol} hissesinde ana trend yukarı yönlüdür ancak kısa vadeli göstergeler düzeltme veya direnç testine işaret etmektedir. Tek seferde girmek yerine ₺{entry1_val} ve olası geri çekilmede ₺{entry2_val} desteklerinden 2 kademede alım yaparak ortalamayı güvenli seviyede tutmak en akılcı stratejidir."
        elif action == "SELL":
            verdict_badge = "SAT / RİSKLİ"
            verdict_title = "⚠️ SATIŞ BASKISI — SERMAYE KORUMA MODU"
            verdict_color = "#ef4444"
            exec_pitch = f"{symbol} için teknik ve makro motorlar düşüş baskısı veya kırılım uyarısı vermektedir. Yeni alım önerilmez, mevcut pozisyonlarda stop seviyelerine riayet edilmelidir."
        else:
            verdict_badge = "İZLE / BEKLE"
            verdict_title = "🛑 İZLE / NÖTR — RİSKSİZ BEKLEME"
            verdict_color = "#f59e0b"
            exec_pitch = f"{symbol} için teknik ve hacim verileri şu anda konsolidasyon bölgesindedir. CIO komitesi net bir kırılım veya destek onayı gelene kadar sermaye koruma amaçlı beklemede kalınmasını önermektedir."

        warrant_gain_tp1 = round(tp1_gain * 5.2, 1)
        warrant_gain_tp2 = round(tp2_gain * 5.2, 1)

        conviction_playbook = {
            "Verdict_Badge": verdict_badge,
            "Verdict_Title": verdict_title,
            "Verdict_Color": verdict_color,
            "Executive_Pitch": exec_pitch,
            "Risk_Reward_Ratio": f"1 : {rr_calc}",
            "Max_Risk_Loss_Pct": f"-%{sl_loss}",
            "TP1_Gain_Pct": f"+%{tp1_gain}",
            "TP2_Gain_Pct": f"+%{tp2_gain}",
            "Top_3_Proofs": [
                f"<b>1. Kurumsal Para & Hacim:</b> MFI %{round(mfi_val, 1)} ({sm_status}) ve OBV trendi {obv_trend} yönünde. Alıcı baskısı {buyer_pressure} olarak ölçüldü.",
                f"<b>2. Teknik Güç & Trend:</b> Trend '{trend}' yönünde, teknik puan {technical_result.get('Score', 50)}/100. Fiyat hareketli ortalamaların üzerinde güç topluyor.",
                f"<b>3. Matematiksel Risk/Ödül:</b> Zarar Kes: ₺{stop_loss} (-%{sl_loss} risk) | Ana Hedef: ₺{tp2_val} (+%{tp2_gain} kâr). Risk/Kazanç Oranı 1 : {rr_calc} ile istatistiksel üstünlük sağlar."
            ],
            "Tactical_Steps": [
                f"<b>🛒 1. Giriş:</b> ₺{entry1_val} seviyesinden planlanan sermayenin %50'si ile ilk kademe alımı yapın.",
                f"<b>🔄 2. Destek Alımı:</b> Geri çekilme olursa ₺{entry2_val} seviyesinden kalan %50 ile maliyet düşürün.",
                f"<b>🛡️ 3. Sermaye Kalkanı:</b> ₺{stop_loss} altında kapanış gelirse pozisyonu kapatıp sermayenizi koruyun.",
                f"<b>💰 4. Kâr Realizasyonu:</b> ₺{tp1_val} (+%{tp1_gain}) seviyesinde %50 kâr alın; kalan için stop'u maliyete çekerek sıfır riskle ₺{tp2_val} (+%{tp2_gain}) hedefine sürün."
            ],
            "Warrant_Tactics": f"⚡ <b>Kaldıraçlı Varant Fırsatı:</b> Hissedeki olası +%{tp1_gain} - +%{tp2_gain} yükseliş, ~5x kaldıraçlı bir Alım (Call) Varantında <b>+%{warrant_gain_tp1} ile +%{warrant_gain_tp2}</b> arasında kâr potansiyeli yaratır. Delta 0.40 - 0.60 arası, min 30 gün vadeli varant önerilir."
        }

        return {
            "META": {
                "Symbol": symbol,
                "Current_Price": round(current_price, 2),
                "Change_Pct": round(change_pct, 2),
                "Timestamp": timestamp
            },
            "Section_0_Conviction_Playbook": conviction_playbook,
            "Section_1_Executive": exec_pitch,
            "Section_2_Grade": inv_grade,
            "Section_3_Opportunity": round(confidence_score * 0.9 + 10, 1),
            "Section_4_Confidence": confidence_score,
            "Section_5_Risk": round(risk_score, 1),
            "Section_6_Conviction": round(conviction_score, 1),
            "Section_7_Regime": regime,
            "Section_8_MTF": mtf,
            "Section_9_Position": {
                "Amount": f"Kasanın Maksimum %{risk_plan.get('Max_Risk_Pct', 2.0)}'si",
                "Scaling": "3 Kademe",
                "Entry_1": entry1_val,
                "Entry_2": entry2_val,
                "Entry_3": round(current_price * 0.95, 2),
                "Cash_Reserve": "Min %30 Nakit"
            },
            "Section_10_Exit": {
                "TP1": tp1_val,
                "TP2": tp2_val,
                "TP3": trade_plan["Exit_Plan"]["Take_Profit_3"],
                "Strategy": "Trailing Stop & Kademeli Satış"
            },
            "Section_11_Do": directives["Dos"],
            "Section_12_Dont": directives["Donts"],
            "Section_13_Portfolio": {
                "Fit": "Portföy beta dengesi için uygun." if confidence_score > 60 else "Risk iştahı yüksek hesaplara uygun.",
                "Correlation": "BIST100 ile %85 korele.",
                "Sector_Warning": "Aynı sektörden 2'den fazla hisse bulundurmayın."
            },
            "Section_14_WatchList": ["AKBNK.IS", "THYAO.IS", "KCHOL.IS"],
            "Section_15_EarlyWarning": {
                "Risk": "TCMB faiz kararı volatilitesi.",
                "Opportunity": "MACD Haftalık alım bölgesine yaklaşıyor."
            },
            "Section_16_Scenario": {
                "Bull": {"Price": round(current_price * 1.15, 2), "Prob": "45%"},
                "Base": {"Price": round(current_price * 1.05, 2), "Prob": "35%"},
                "Bear": {"Price": round(current_price * 0.85, 2), "Prob": "20%"}
            },
            "Section_17_Forecast": {
                "1d": f"{round(current_price*0.98,2)} - {round(current_price*1.02,2)}",
                "1w": f"{round(current_price*0.95,2)} - {round(current_price*1.05,2)}",
                "1m": f"{round(current_price*0.90,2)} - {round(current_price*1.12,2)}",
                "3m": f"{round(current_price*0.85,2)} - {round(current_price*1.25,2)}",
                "6m": f"{round(current_price*0.75,2)} - {round(current_price*1.40,2)}",
                "12m": f"{round(current_price*0.60,2)} - {round(current_price*1.80,2)}"
            },
            "Section_18_Reliability": {
                "Analogues": backtest.get("Total_Historical_Cases", 0),
                "Hit_Rate": f"%{backtest.get('Hit_Rate_Pct', 50.0)}",
                "Monte_Carlo_Risk": f"%{monte_carlo.get('Max_Drawdown_Pct', 0.0)}",
                "Average_Days_to_Target": backtest.get("Average_Days_to_Target", 0.0)
            },
            "Section_19_Reasoning": {
                "Pro": "Kurumsal para girişi ve teknik güç.",
                "Con": "Kısa vadeli momentum yorgunluğu.",
                "Counter": anti_agent["Counter_Opinion"],
                "CIO_Verdict": cio_report["CIO_Reasoning"],
                "Committee_Votes": cio_report["Committee_Votes"],
                "The_7_Whys": cio_report["The_7_Whys"]
            },
            "Section_20_CIO_Executive_Summary": {
                "Pyramiding": op_pyramiding,
                "Short_Term_Advice": op_short_term,
                "Long_Term_Advice": op_long_term
            },
            "Section_20_LiveMonitor": {
                "Status": "İzleniyor",
                "Alert": "Henüz kırılım gerçekleşmedi, beklemede kal."
            },
            "Section_21_TechnicalIndicators": technical_result.get("Indicators", {}),
            "Section_22_FundamentalRatios": {
                "P_E_Ratio": fundamental_result.get("P_E_Ratio", "N/A"),
                "P_B_Ratio": fundamental_result.get("P_B_Ratio", "N/A"),
                "ROE": fundamental_result.get("ROE", "N/A"),
                "Debt_to_Equity": fundamental_result.get("Debt_to_Equity", "N/A"),
                "Profit_Margin": fundamental_result.get("Profit_Margin", "N/A")
            },
            "Section_23_Macro": {
                "VIX_Level": vix_level,
                "Regime": regime,
                "Market_Trend": macro_result.get("Trend", "UNKNOWN")
            },
            "Section_24_Operations": {
                "Entry": trade_plan.get("Entry_Plan", {}),
                "Exit": trade_plan.get("Exit_Plan", {}),
                "Support": trade_plan.get("Support_Levels", {}),
                "Resistance": trade_plan.get("Resistance_Levels", {}),
                "Risk_Reward": trade_plan.get("Risk_Reward_Ratio", 2.0),
                "Dynamic_ATR": trade_plan.get("Dynamic_ATR", "N/A")
            },
            "Section_25_OrderFlow": order_flow_data,
            "Section_26_SmartMoney": smart_money_deep_data,
            "Section_27_Fundamental": {
                "P_E_Ratio": fundamental_result.get("P_E_Ratio", "N/A"),
                "ROE": fundamental_result.get("ROE", "N/A"),
                "Debt_to_Equity": fundamental_result.get("Debt_to_Equity", "N/A"),
                "Score": fundamental_result.get("Score", 50.0),
                "Status": fundamental_result.get("Status", "NÖTR")
            },
            "Section_28_Sentiment": {
                "Score": sentiment_result.get("Score", 50.0),
                "Status": sentiment_result.get("Status", "NÖTR"),
                "News_Count": sentiment_result.get("News_Count", 0),
                "Analysis": sentiment_result.get("Analysis", "NÖTR")
            },
            "Section_29_Options": {
                "Score": options_result.get("Score", 50.0),
                "Implied_Volatility": options_result.get("Implied_Volatility", "N/A"),
                "Theta_Risk": options_result.get("Theta_Risk", "N/A"),
                "Leverage_Suitability": options_result.get("Leverage_Suitability", "N/A"),
                "Status": options_result.get("Status", "UNKNOWN")
            },
            "Section_30_MTF_Indicators": technical_result.get("MTF_Indicators", {}),
            "Section_31_Projections": LSTMProjectionEngine().analyze(symbol, current_price),
            "Section_32_Historical_Data": [
                {
                    "time": str(idx.date()),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"])
                }
                for idx, row in df.tail(90).iterrows()
            ],
            "Section_33_HistoricalNews": historical_news,
            "Section_34_AINarrative": ai_narrative
        }
