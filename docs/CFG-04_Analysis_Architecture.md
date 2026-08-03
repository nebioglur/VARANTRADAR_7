# CFG-04: ANALYSIS ARCHITECTURE
**Sistemin Kasları: Analiz Katmanı Standartları**

Veri (Data Architecture) sisteme girdikten sonra, yapay zekanın Karar Motoruna (Decision Architecture) gitmeden önce devasa bir "Matematiksel Filtreleme" sürecinden geçer. Bu belge, VarantRadar Pro'nun kaslarını oluşturan yedi (7) ana analiz motorunun nasıl çalışacağını ve neleri filtreleyeceğini tanımlar. Hiçbir analiz motoru tek başına nihai kararı (Al/Sat) verme yetkisine sahip değildir; sadece "Skor" üretirler.

---

## 1. Trend & Momentum Analizi (Technical Core)
Fiyat hareketlerinin mekaniğini çözer.
- **Trend Tanıma:** Sadece hareketli ortalamalara (EMA 20, 50, 200) bakmaz; tepe ve dip yapılarının (Higher Highs, Lower Lows) geometrisini analiz ederek ana akımı belirler.
- **Momentum:** Fiyatın yükseliş veya düşüş ivmesini (Velocity) hesaplar (RSI, MACD Divergence, ROC). 
- *Kural:* Trende karşı olan Momentum (örn: düşüş trendinde şişmiş RSI) sahte (Fakeout) kabul edilir ve algoritmik skor cezalandırılır.

## 2. Smart Money (Akıllı Para / Hacim Analizi)
Sıradan perakende uygulamalarının yapamadığı, kurumsal likiditeyi izleyen motordur.
- **Volume Profiling:** Hangi fiyat kademelerinde büyük para takas edildi? (Point of Control - POC).
- **Kurumsal Ayak İzi:** VWAP (Hacim Ağırlıklı Ortalama Fiyat) etrafındaki sapmalar ve Wyckoff döngüleri (Akümülasyon/Dağıtım aşamaları) saptanır. Fiyat artarken hacim düşüyorsa, sistem bunu "Büyük yatırımcı mal çıkıyor (Dağıtım)" olarak okur.

## 3. Fundamental (Temel / Bilanço Analizi)
Hissenin arkasındaki şirketin mali sağlığını analiz eder. Sadece kâra değil, kalitesine bakar.
- F/K, PD/DD, FAVÖK marjı, Özsermaye Karlılığı (ROE) ve Borç/Özkaynak oranları hesaplanır.
- **Şirket Kalitesi:** İflas veya manipülasyon riskine karşı Piotroski F-Score ve Altman Z-Score testleri uygulanarak "Temel Sağlık Skoru" (0-100) çıkarılır.

## 4. Quant (Kantitatif Analiz & Faktör Modelleri)
Piyasadaki diğer hisselere kıyasla varlığın "Göreceli Gücünü" ölçer.
- **Multi-Factor Ranking:** Hisse; Değer (Value), Büyüme (Growth), Momentum ve Volatilite faktörlerine göre puanlanır.
- İstatistiksel Anomaliler (Bollinger Band sıkışmaları, Mean Reversion) kantitatif olarak doğrulanır.

## 5. Macro (Makroekonomik Piyasa Rejimi)
Gemi fırtınaya giriyorsa, yelkenlerin ne kadar sağlam olduğunun bir önemi yoktur.
- BIST100 (veya SP500, CDS Primi, Döviz Sepeti vb.) genel durumu incelenir.
- Piyasa Rejimi: "Boğa", "Ayı", "Yüksek Volatilite", "Yatay" olarak etiketlenir.
- *Kural:* Eğer makro rejim "Ayı" ise, teknik analizi harika olan bir hissenin bile Başarı Olasılığı (Probability of Success) formülasyonda otomatik olarak düşürülür.

## 6. News & Sentiment (Haber ve Duyarlılık)
Verilerin anlatamadığı psikolojiyi okur.
- KAP bildirimleri, sektörel haberler ve (mümkünse) sosyal medya/forum tartışmaları NLP (Doğal Dil İşleme) süzgecinden geçirilir.
- "Korku mu hakim, Açgözlülük mü?" sorusuna 0-100 arası bir Sentiment Skoru verilir.
- *Kural:* Ani bir negatif haber (Kriz/Dava/Savaş vb.), teknik göstergeler kusursuz olsa dahi işlemi anında "İptal (Invalidation)" edebilir.

## ÖZET (Çıktı Sınırı)
Bu yedi analiz motorunun tek amacı, CFG-05 (Decision Architecture) motoruna **saf, ağırlıklandırılabilir ve standardize edilmiş "Skorlar" (0-100) ve "Durum Etiketleri"** yollamaktır. Hiçbir analiz motoru kullanıcıya direkt olarak "İşlem yap" diyemez.
