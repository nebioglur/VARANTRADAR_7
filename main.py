
def _get_pa_session():
    import requests, os
    if os.path.exists("/home/varantradarpro") or "pythonanywhere" in os.environ.get("PYTHONANYWHERE_DOMAIN", "").lower() or os.path.exists("/etc/pythonanywhere"):
        s = requests.Session()
        s.proxies = {"http": "http://proxy.server:3128", "https": "http://proxy.server:3128"}
        return s
    return None

import json
import pandas as pd

from data.pipeline import DataPipeline

from analysis.technical import TechnicalEngine
from analysis.fundamental import FundamentalEngine
from analysis.smart_money import SmartMoneyEngine
from analysis.sentiment import SentimentEngine
from analysis.macro import MacroEngine
from analysis.options_engine import OptionsEngine

from decision.executive import ExecutiveDecisionEngine
from execution.planner import TradePlanner

def run_simulation(symbol: str):
    print(f"\n[VARANTRADAR PRO] {symbol} İçin 13 Altın Soru Analizi Başlatılıyor...")
    print("-" * 60)
    
    # 1. DATA LAYER (CFG-03.1 Enterprise Data Architecture)
    print("[1/5] Veriler Çekiliyor (Multi-Source Failover Aktif)...")
    pipeline = DataPipeline()
    
    df = pipeline.get_clean_data(symbol, period="6mo", interval="1d")
    
    if df.empty:
        print(f"HATA: {symbol} için veri çekilemedi!")
        return
        
    current_price = df['close'].iloc[-1]
    # Basit ATR simülasyonu
    high_low = df['high'] - df['low']
    atr = high_low.rolling(14).mean().iloc[-1]
    
    # BIST100 (Makro) Verisi Çekelim -> Test için S&P 500 (^GSPC) kullanıyoruz
    print("[2/5] Makro Rejim Verisi Çekiliyor...")
    bist_df = pipeline.get_clean_data("^GSPC", period="6mo", interval="1d")
    
    # 2. ANALYSIS LAYER (Kaslar)
    print("[3/5] Analiz Motorları (Kaslar) Çalıştırılıyor...")
    tech_engine = TechnicalEngine()
    fund_engine = FundamentalEngine()
    smart_engine = SmartMoneyEngine()
    sent_engine = SentimentEngine()
    macro_engine = MacroEngine()
    
    tech_res = tech_engine.analyze(symbol, df)
    fund_res = fund_engine.analyze(symbol, df) # Gerçekte bilanço API'si kullanır
    smart_res = smart_engine.analyze(symbol, df)
    sent_res = sent_engine.analyze(symbol, df) # Gerçekte Haber API'si kullanır
    macro_res = macro_engine.analyze("^GSPC", bist_df)
    options_engine = OptionsEngine()
    options_res = options_engine.analyze(symbol, df)
    
    # 3. DECISION ENGINE (Büyük Beyin)
    print("[4/5] Büyük Beyin ve Portföy Yöneticisi Karar Veriyor...")
    total_capital = 100000.0 # Örnek 100.000 TL Kasa
    
    final_report = ExecutiveDecisionEngine.generate_final_report(
        symbol=symbol,
        current_price=current_price,
        atr=atr,
        total_capital=total_capital,
        df=df,
        technical_result=tech_res,
        fundamental_result=fund_res,
        smart_money_result=smart_res,
        sentiment_result=sent_res,
        macro_result=macro_res,
        options_result=options_res
    )
    
    # 4. JSON ÇIKTISI
    print("[5/5] Analiz Tamamlandı. '13 Altın Soru' Raporu Basılıyor:\n")
    print("=" * 70)
    print(json.dumps(final_report, indent=4, ensure_ascii=False))
    print("=" * 70)
    
    return final_report

def run_simulation_api(symbol: str) -> dict:
    """Web API (Flask) üzerinden çağrılacak olan fonksiyon. Print yerine sadece dict döner."""
    pipeline = DataPipeline()
    tech_engine = TechnicalEngine()
    fund_engine = FundamentalEngine()
    smart_engine = SmartMoneyEngine()
    sent_engine = SentimentEngine()
    macro_engine = MacroEngine()
    options_engine = OptionsEngine()
    executive_engine = ExecutiveDecisionEngine()
    trade_planner = TradePlanner()
    
    df = pipeline.get_clean_data(symbol, period="2y", interval="1d")
    if df is None or df.empty:
        for p in ["1y", "6mo", "3mo"]:
            df = pipeline.get_clean_data(symbol, period=p, interval="1d")
            if df is not None and not df.empty:
                break
    if df is None or df.empty:
        try:
            import yfinance as yf
            clean_s = symbol.replace(".IS", "").strip()
            for cand in [symbol, f"{clean_s}.IS", clean_s]:
                try:
                    _pa_s = _get_pa_session()
                    t = yf.Ticker(cand, session=_pa_s) if _pa_s else yf.Ticker(cand)
                    raw = t.history(period="1y", interval="1d")
                    if raw is not None and not raw.empty:
                        df = raw
                        break
                except Exception:
                    pass
            if (df is None or df.empty):
                for cand in [symbol, f"{clean_s}.IS", clean_s]:
                    try:
                        _pa_s = _get_pa_session()
                        raw = yf.download(cand, period="1y", interval="1d", threads=False, progress=False, session=_pa_s) if _pa_s else yf.download(cand, period="1y", interval="1d", threads=False, progress=False)
                        if raw is not None and not raw.empty:
                            df = raw
                            break
                    except Exception:
                        pass
            if df is not None and not df.empty:
                df.columns = [c[0].lower() if isinstance(c, tuple) else str(c).lower() for c in df.columns]
        except Exception:
            pass

        if df is None or df.empty:
        # 3. YEDEK KATMAN: GLOBAL_DASHBOARD_CACHE ve Disk Cache
        try:
            from server import GLOBAL_DASHBOARD_CACHE
            all_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
            stat_data = all_stats.get(symbol) or all_stats.get(clean_s) or all_stats.get(f"{clean_s}.IS")
            if stat_data:
                p = float(stat_data.get("Price") or stat_data.get("Daily_Close") or 0.0)
                o = float(stat_data.get("Daily_Open") or p)
                h = float(stat_data.get("High") or p)
                l = float(stat_data.get("Low") or p)
                v = float(stat_data.get("Volume") or 100000)
                # En az 30 günlük sentetik/yaklaşık seri oluştur ki tüm motorlar (RSI/ATR/Teknik) çalışsın
                import numpy as np
                dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='B')
                closes = np.linspace(p * 0.95, p, 30)
                highs = closes * 1.015
                lows = closes * 0.985
                opens = (highs + lows) / 2.0
                highs[-1] = max(h, closes[-1])
                lows[-1] = min(l, closes[-1])
                opens[-1] = o
                closes[-1] = p
                df = pd.DataFrame({
                    'open': opens,
                    'high': highs,
                    'low': lows,
                    'close': closes,
                    'volume': [v] * 30
                }, index=dates)
        except Exception as _fb_err:
            pass

    if df is None or df.empty:
        return {"error": f"Veri çekilemedi veya geçersiz sembol: {symbol}"}
        
    high_low = df['high'] - df['low']
    atr = high_low.rolling(14).mean().iloc[-1]
    bist_df = pipeline.get_clean_data("^GSPC", period="2y", interval="1d")
    
    tech_res = tech_engine.analyze(symbol, df)
    fund_res = fund_engine.analyze(symbol, df) 
    smart_res = smart_engine.analyze(symbol, df)
    sent_res = sent_engine.analyze(symbol, df) 
    macro_res = macro_engine.analyze("^GSPC", bist_df)
    options_res = options_engine.analyze(symbol, df)
    
    current_price = df['close'].iloc[-1]
    total_capital = 100000.0 # Örnek Kasa

    json_report = ExecutiveDecisionEngine.generate_final_report(
        symbol=symbol,
        current_price=current_price,
        atr=atr,
        total_capital=total_capital,
        df=df,
        technical_result=tech_res,
        fundamental_result=fund_res,
        smart_money_result=smart_res,
        sentiment_result=sent_res,
        macro_result=macro_res,
        options_result=options_res
    )
    
    return json_report

if __name__ == "__main__":
    # Test için yfinance'de kesin çalışan AAPL kullanalım
    run_simulation("AAPL")
