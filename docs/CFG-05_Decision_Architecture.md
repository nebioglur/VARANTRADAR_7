# CFG-05: DECISION ARCHITECTURE
**Sistemin Beyni: AI Karar ve Olasılık Katmanı**

Bu belge, VarantRadar Pro'nun tüm sistemini birleştiren "Beyin" (Executive Decision Engine) yapısının nasıl düşündüğünü, nasıl şüphe duyduğunu ve nasıl nihai bir Karar (Rapor) üreteceğini tanımlayan en kritik mimari standarttır.

---

## 1. Multi-Dimensional Scoring (Çok Boyutlu Puanlama)
Analiz mimarisindeki (CFG-04) tüm motorlardan gelen skorlar (0-100), AI Yöneticisi (Executive Engine) tarafından sabit ağırlıklarla değil, "Piyasa Rejimine Göre Dinamik Ağırlıklarla" çarpılarak birleşir.

- *Örnek (Boğa Piyasasında):* Teknik Trend (%40), Smart Money (%30), Temel Bilanço (%15), Duyarlılık (%15).
- *Örnek (Ayı Piyasasında):* Risk yönetimi öne çıkar. Temel Bilanço (%40), Smart Money (%30), Teknik Trend (%20), Duyarlılık (%10).
- Bu dinamik puanlama sonucunda **Base Confidence Score (Temel Güven Skoru)** elde edilir.

## 2. Trade Quality (İşlem Kalitesi) Çarpanları
Sadece "Yükselecek" tahmini yapmak yeterli değildir. Sistemin o işleme girmesinin ne kadar "Kaliteli" olduğu hesaplanır (Trade Quality Score: A+, B, C vb.).
- **R/R (Risk-Getiri):** 1:3 altındaki işlemlerin kalitesi Düzeltme yer.
- **Likidite Skoru:** Tahtası sığ olan bir varlık, teknik puanı 100/100 bile olsa, "Trade Quality" üzerinden büyük ceza yer. Çünkü giriş yapılabilir ancak çıkış (Stop) patlayabilir.
- **Formasyon Temizliği:** Trend gürültülü mü (whipsaw), yoksa pürüzsüz mü akıyor? Pürüzsüz trendler A+ kalite alır.

## 3. Explainable AI ve Şeytanın Avukatı (Counter Opinion)
Sistemin körü körüne alım vermesini engellemek için AI bir nevi "Şizofrenik" bir yapıyla çalışır. Karar verici (Pro-Agent) işlem fikrini sunduktan sonra, **Şeytanın Avukatı (Anti-Agent)** bu tezi çürütmeye çalışır.

- **Counter Opinion Süreci:** Anti-Agent bilerek sistemdeki en zayıf halkayı bulur (Örn: "Trend harika ama şirketin borç oranı sektör ortalamasının 3 katı").
- Karar verici bu itirazı kendi risk modeline katar. Eğer itiraz kritikse, Güven Skoru (Confidence) düşürülür.
- Kullanıcıya sunulan CFG-01 Raporunda *"AI Açıklaması"* bölümünde bu tartışma özetlenir (Neden bu karar alındı, olası tuzaklar nelerdir).

## 4. Olasılık Hesaplamaları (Probability Matrix)
VarantRadar "Kesinlikle Yükselecek" demez. "Hedefe Ulaşma İhtimali %84" der. Bu olasılık nasıl hesaplanır?
1. **Historical Similarity (Tarihsel Benzerlik):** Algoritma, mevcut hissenin son 10 günlük kurulumunu alır ve veri tabanında (son 10 yılda) bu kalıba tıpatıp uyan fraktalları bulur.
2. **Backtest Hit-Rate:** Bulunan yüzlerce (örn: 482 adet) benzer durumun yüzde kaçı geçmişte hedefe ulaşmış? (Örn: %82.9)
3. **Piyasa Faktörü:** Geçmişteki o günlerle bugünün piyasa rejimi (Faizler, CDS) aynı mı? Değilse oran aşağı/yukarı revize edilir.
4. **Sonuç:** Net ve istatistiksel bir *Başarı Olasılığı Yüzdesi (%X)*.

## 5. İptal Şartları (Invalidation Conditions)
Bir karar raporu üretildiğinde, o kararın ne zaman "Çöpe Atılacağı" baştan belirlenir.
- **Örnek:** "Bu alım raporu geçerlidir, **ANCAK** fiyat 22.40 TL desteğinin altına inerse (Stop Loss) VEYA FED faizleri artırırsa bu karar anında geçersiz (Invalid) sayılır."
- Bu mantık, kullanıcının rapora duygusal olarak bağlanmasını engeller ve matematiksel bir çıkış (Exit) stratejisi sunar.

## ÖZET
CFG-05 Decision Architecture, binlerce veriyi alıp, birbirleriyle dövüştürüp, şeytanın avukatlığını yapıp, geçmiş 10 yılın tarihsel ispatını bulup, en sonunda CFG-01 (Yatırım Değerlendirme Raporu) formatında o meşhur, kusursuz istatistiksel metni ("Bu işlem %84,7 hedefe ulaşma olasılığı...") basan matbaanın ta kendisidir.
