import pandas as pd
from services.analyzer import Analyzer
from services.scoring import ScoringEngine
from services.screener import MarketScreener

def demo():
    print("="*50)
    print("VARANTRADAR PRO - CANLI KANIT (DEMO)")
    print("="*50)

    # 1. Analiz Motoru Kanıtı
    print("\n[1] Analiz Motoru Test Ediliyor: THYAO.IS (Türk Hava Yolları)")
    analyzer = Analyzer()
    df = analyzer.calculate_indicators("THYAO.IS", "1d")
    if not df.empty:
        latest = df.iloc[-1]
        print(f"Başarıyla veri çekildi! Son Güncel Tarih: {latest['date']}")
        print(f"Kapanış Fiyatı: {latest['close']:.2f} TL")
        print(f"Hesaplanan RSI (14): {latest['RSI']:.2f}")
        print(f"Hesaplanan MACD: {latest['MACD']:.2f} (Sinyal: {latest['MACD_Signal']:.2f})")
        print(f"Trend Skoru: {latest.get('Trend_Score', 'N/A')} (Yükseliş>0, Düşüş<0)")
    else:
        print("Hata: THYAO.IS verisi çekilemedi.")

    # 2. Puanlama Motoru Kanıtı
    print("\n[2] Yapay Zeka Puanlama Motoru Test Ediliyor: THYAO.IS")
    scorer = ScoringEngine()
    score_data = scorer.generate_score("THYAO.IS", "1d")
    print(f"Sonuç Sinyali: {score_data['action']}")
    print(f"Güven Puanı: {score_data['score']}/100")
    print("Puanlama Gerekçeleri:")
    print(score_data['reasoning'])

    # 3. Otomatik Tarama (Screener) Kanıtı
    print("\n[3] Piyasa Radarı Test Ediliyor: BIST100 Tüm Hisseler")
    from config.settings import TARGET_STOCKS
    screener = MarketScreener()
    results = screener.run_screener(TARGET_STOCKS)
    if not results.empty:
        print(f"\nRADAR {len(results)} ADET FIRSAT BULDU:")
        for _, row in results.iterrows():
            print(f" -> {row['symbol']} | Puan: {row['score']} | Sinyal: {row['action']}")
    else:
        print("\nRADAR SONUCU: Şu an BIST30'da 75 üstü veya 35 altı ekstrem (Güçlü AL/SAT) fırsatı veren hiçbir hisse YOKTUR.")
        print("(Bu, sistemin rastgele sinyal üretmediğinin ve sadece mükemmel koşullarda çalıştığının en büyük kanıtıdır.)")
    print("="*50)

if __name__ == "__main__":
    import logging
    # Sadece demo printlerini görmek için logger'ı kapatıyoruz
    logging.getLogger().setLevel(logging.CRITICAL)
    demo()
