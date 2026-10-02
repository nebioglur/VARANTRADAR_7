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
