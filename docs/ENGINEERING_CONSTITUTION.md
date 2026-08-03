# 📘 VARANTRADAR PRO ENGINEERING CONSTITUTION
*(Project Constitution • Architecture Rulebook • Master Development Roadmap)*

Bu belge VarantRadar Pro'nun **Tek Doğruluk Kaynağıdır (Single Source of Truth).** Yazılacak her modül, her engine, her CFG ve her V sürümü bu anayasaya uygun olmak zorundadır.

---

## BÖLÜM 1 — PROJENİN MİSYONU
- **Projenin Amacı:** Milyonlarca finansal veriyi sentezleyerek kullanıcıya istatistiksel ispatı olan, açıklanabilir (XAI) işlem planları sunmak.
- **Çözmek İstediği Problemler:** Duygusal kararlar, risk yönetimindeki eksiklikler, bilgi kirliliği ve asılsız "tüyo" temelli işlemlerin engellenmesi.
- **Hedef Kullanıcı Kitlesi:** Bireysel yatırımcılar, profesyonel traderlar ve kurumsal portföy yöneticileri.
- **Rakip Analizi:** Geleneksel tarayıcılar (Scanner) sadece sinyal üretir. VarantRadar ise bir "Sinyal Sağlayıcı" değil, uçtan uca otonom bir "Hedge Fon Yöneticisidir".
- **VarantRadar'ın Farkı:** İşlemleri sadece üretmez; istatistiksel olarak (Backtest/Monte Carlo) ispatlar, riskini hesaplar ve "Yapay Zeka Karar Gerekçesini" açıklar.
- **Neden Geliştiriliyor?** Yatırımcıların karar süreçlerini profesyonel, veri odaklı ve makine keskinliğinde bir standarda oturtmak için.
- **Başarı Kriterleri:** Otonom analiz yeteneği, %70+ istikrarlı başarı oranı, 0 iflas (Ruin) riski ve kullanıcıya net, açıklanabilir güven (Confidence).

## BÖLÜM 2 — VİZYON
- **1 Yıllık Hedef:** BIST hisse ve varant pazarında kusursuz çalışan, veri odaklı AI analiz platformunu oturtmak.
- **3 Yıllık Hedef:** Kullanıcıların kendi portföylerini bağlayabildiği otonom uyarı ve yönetim ekosistemine dönüşmek.
- **5 Yıllık Hedef:** Global borsalara entegre edilmiş, çoklu dil destekli otonom bir AI Hedge Fonu altyapısına sahip olmak.
- **Enterprise Hedefi:** Banka ve aracı kurumlara API ve SDK üzerinden VarantRadar zekasını satabilmek.
- **Global Hedef:** Tüm dünya borsalarında (NASDAQ, Crypto, Forex) çalışabilen evrensel bir analiz beyni oluşturmak.
- **AI Hedefi:** Kendi kararlarını analiz eden, hatalarından öğrenen (Learning Engine) süper zeki bir varlık olmak.
- **Kullanıcı Deneyimi Hedefi:** Karmaşıklığı gizleyip, en gelişmiş kantitatif matematiği bile basit "13 Soru" raporuyla sunabilmek.

## BÖLÜM 3 — TEMEL PRENSİPLER
1. **Karar Destek Sistemi:** Sadece gösterge sunmaz, karar verir ve savunur.
2. **Açıklanabilir AI (XAI):** "Ben böyle hesapladım" demez, hangi motorun ne kadar katkı yaptığını ispatlar.
3. **Veri Odaklı Yaklaşım:** Söylentilere değil, OHLCV ve Order Flow verisine güvenir.
4. **Şeffaflık:** Yanılma payını, başarı olasılığını ve Max Drawdown riskini açıkça söyler.
5. **İstatistiksel Doğrulama:** Backtest veya Monte Carlo onayı olmadan strateji asla dışarı çıkmaz.
6. **Sürekli Öğrenme:** Kapanan işlemleri analiz edip model ağırlıklarını optimize eder.
7. **Modüler Mimari:** CFG (Component Flow Graph) standartlarıyla her katman izole çalışır.
8. **Performans:** Threading ve Async yapılarla binlerce hisseyi saniyeler içinde tarar.
9. **Güvenlik:** API anahtarları, portföy verileri yüksek şifrelemeyle korunur.
10. **Ölçeklenebilirlik:** Mikroservis ve Event-Driven mimariyle dünya çapında çalışmaya hazırdır.

---

## BÖLÜM 4 — VARANTRADAR ANAYASASI (13 ALTIN KURAL)
**Bu bölüm projenin en önemli kısmıdır. Hiçbir modül bu kuralları ihlal edemez.**
Her AI önerisi aşağıdaki 13 soruyu **eksiksiz** cevaplamak zorundadır:

1. **Neden bu hisse/varant seçildi?** Teknik, Temel, Smart Money, Makro etkiler ve sentezlenmiş AI Karar Gerekçesi.
2. **Şu an işlem yapılmalı mı?** Sistem durum tespiti yapmaz, net bir eylem (Action Level) kararı verir.
3. **En uygun giriş seviyesi neresi?** En iyi giriş fiyatı, Kademeli Alım Bölgeleri (DCA) ve FOMO Uyarısı.
4. **Stop-Loss nerede olmalı?** Zarar kesmek esnetilemez bir kanundur. ATR, Dinamik ve AI Stop Önerisi.
5. **Kâr alma hedefleri neler?** TP1, TP2, TP3 ve R/R Analizi.
6. **İşlem ne kadar sürebilir?** Tahmini hedefe ulaşma süresi (Gün/Hafta).
7. **Başarı olasılığı nedir?** AI Güven Skoru, Hedefe ulaşma ihtimali, Beklenen Getiri/Zarar ve Max Drawdown.
8. **Bu öneriyi destekleyen gerekçeler nelerdir?** Hangi motorun ne kadar katkı yaptığı gösterilir (Katkı Analizi).
9. **Çoklu Zaman Dilimi (Multi-Timeframe) hedefleri neler?** Günlük, Haftalık ve Aylık periyotların sentezi.
10. **Hangi koşullarda öneri geçersiz olur? (Invalidation)** Analiz ne zaman çöpe atılır?
11. **Tarihsel İstatistiksel Başarı (Validation)?** Walk-Forward, Monte Carlo ve Backtest Sonuçları.
12. **Pozisyon Büyüklüğü ve Sermaye Yönetimi?** Portföyün maksimum yüzde kaçı bu işleme ayrılmalı? (Ruin Risk)
13. **Likidite, Korelasyon ve Hedge İhtiyacı?** Tahtada kayma (Slippage) riski var mı? VİOP Hedge öneriliyor mu?

---

## BÖLÜM 5 — MASTER ROADMAP
- **Phase 0:** Foundation (Temel altyapı ve mimari iskelet)
- **Phase 1:** Data Layer (Veri boru hatları ve temizlik)
- **Phase 2:** Analysis Layer (Teknik, Temel, Makro motorlar)
- **Phase 3:** Scanner Layer (Evrensel paralelleştirilmiş tarayıcı)
- **Phase 4:** Scoring Layer (0-100 Puanlama standartları)
- **Phase 5:** Decision Engine (Büyük Beyin ve Şeytanın Avukatı)
- **Phase 6:** Trade Planner (Giriş, Çıkış, R/R Hesaplayıcısı)
- **Phase 7:** Validation (Monte Carlo ve Backtest simülatörleri)
- **Phase 8:** Portfolio Intelligence (Risk ve Hedge yöneticisi)
- **Phase 9:** AI Ecosystem (LLM tabanlı Copilot ve Raporlama)
- **Phase 10:** Enterprise (API, Güvenlik, Kurumsal SDK)
- **Phase 11:** Autonomous AI Trader (Nihai otonomi, aracı kurum emir iletimi)

## BÖLÜM 6 — CFG MİMARİSİ
*(Her CFG izole, test edilebilir ve bağımsız bir Domain'i temsil eder)*
- **CFG-01:** Foundation (Core utilities, loglama, hata yönetimi)
- **CFG-02:** Data (YFinance, Matriks, BIST veri bağlayıcıları)
- **CFG-03:** Analysis (Kaslar: Trend, Momentum, Smart Money)
- **CFG-04:** Scanner (Multithreading tarama yöneticisi)
- **CFG-05:** AI Decision (Karar Sentezi, Ağırlıklandırma)
- **CFG-06:** Validation (İstatistiksel Onay Mekanizmaları)
- **CFG-07:** Portfolio (Kasa yönetimi, Margin, Korelasyon)
- **CFG-08:** AI Intelligence (Prompt Motorları, NLP Sentezi)
- **CFG-09:** Market Intelligence (Makro rejim tespiti, Haber Duyarlılığı)
- **CFG-10:** Enterprise (Microservices, Docker, API Gateways)

## BÖLÜM 7 — VERSİYON YOL HARİTASI
- **V1 (Temel Sistem) ➔ V2 (Teknik Analiz) ➔ V3 (Radar) ➔ V4 (Smart Money) ➔ V5 (AI Karar)**
- **V6 (Backtest) ➔ V7 (Portföy) ➔ V8 (AI Copilot) ➔ V9 (Financial Intelligence)**
- **V10 (Enterprise) ➔ V11 (Trade Planner) ➔ V12 (Autonomous AI Trader)**

## BÖLÜM 8 — CORE ENGINE MİMARİSİ
Proje, her biri kendi işinden sorumlu "Engine"ler üzerinden event-driven çalışır:
*Master Engine, Data Engine, Scanner Engine, Analysis Engine, Decision Engine, Risk Engine, Trade Engine, Portfolio Engine, Backtest Engine, Notification Engine, Report Engine, AI Engine, Learning Engine, Monitoring Engine, Security Engine, Plugin Engine.*

## BÖLÜM 9 — AI DECISION ARCHITECTURE
- **AI Nasıl Düşünür?** Veri toplar -> Skorlar -> Rejime göre ağırlıklandırır -> Çürütmeye çalışır (Anti-Agent) -> Karar verir.
- **Puanlama:** 0-100 arası standardize edilmiştir.
- **Confidence Score:** Motorların ağırlıklı toplamından, şeytanın avukatının itirazlarının düşülmesiyle oluşan nihai "Güven" puanı.
- **Explainable AI (XAI):** "Neden 85 puan verdim?" sorusunu her motorun katkı yüzdesini basarak gösterir.

## BÖLÜM 10 — AI TRADE PLANNER
Bu bölüm tamamen kullanıcıya işlem planı üretir: *Giriş, Stop, TP1, TP2, TP3, Risk, Süre, Olasılık, İşlem Kalitesi, Trade Score.*

## BÖLÜM 11 — VALIDATION
İstatistiksel Onay Yöntemleri: *Backtest, Walk Forward, Monte Carlo, Bootstrap, Accuracy, Precision, Recall, F1, Sharpe, Sortino, Calmar, Drawdown.*

## BÖLÜM 12 — AI LEARNING
Sistem canlıya alındığında tahminlerini veritabanına yazar. Daha sonra fiyat o noktaya gitti mi diye kontrol edip (Gerçekleşen sonuçlar), kendi hatalarını analiz ederek ağırlıklarını (Weight) otomatik günceller.

## BÖLÜM 13 — UI / UX STANDARTLARI
Gelecekte yazılacak arayüz için kurallar: *Dashboard, Kartlar, Renkler, Grafikler (TradingView entegrasyonu), Mobil & Masaüstü uyumluluğu, Widget Yapısı, Erişilebilirlik.*

## BÖLÜM 14 — TEST STANDARTLARI
Yazılımın kalitesi: *Unit Test, Integration Test, Regression Test, Performance Test, Stress Test, Security Test, Acceptance Test.*

## BÖLÜM 15 — ENTERPRISE STANDARTLARI
Kurumsallaşma: *API, SDK, Plugin, CI/CD, Docker, Kubernetes, Monitoring, Audit, Logging, Backup, Recovery, Security.*

## BÖLÜM 16 — KODLAMA STANDARTLARI
Mühendislik displini: *SOLID, Clean Architecture, DDD, Hexagonal, Event Driven, Microservice, Dependency Injection, Async, Code Review, Documentation.*

## BÖLÜM 17 — YASAKLAR
- AI gerekçesiz öneri **veremez.**
- Backtest yapılmadan strateji **yayınlanamaz.**
- Risk analizi (Pozisyon Büyüklüğü) olmadan işlem **önerilemez.**
- Confidence Score olmayan öneri **gösterilemez.**
- Stop-loss ve hedef fiyatı olmayan öneri **sunulamaz.**
- İstatistiksel doğrulaması olmayan AI önerisi **yayınlanamaz.**

---

## BÖLÜM 18 — NİHAİ HEDEF & SON İLKE
**VarantRadar'ın amacı:** Yatırımcıya yüzlerce karmaşık gösterge göstermek DEĞİLDİR.
Amaç; milyonlarca veriyi analiz ederek, açıklanabilir yapay zeka ile gerekçelendirilmiş, istatistiksel olarak doğrulanmış ve uygulanabilir işlem planları üretmektir.

**Nihai Kullanıcı Deneyimi:**
Kullanıcı uygulamayı açtığında sistem;
- Binlerce hisse ve varantı otomatik analiz eder ve en güçlü fırsatları önceliklendirir.
- Giriş, stop ve hedef seviyelerini, günlük/haftalık/aylık bazda sunar.
- Risk/Getiri oranını hesaplar, başarı olasılığını verir.
- Karşıt görüşleri değerlendirir ve önerinin ne zaman iptal olacağını (Invalidation) açıklar.
- İşlem kapandıktan sonra kendini eğiterek (Machine Learning) başarı oranını artırır.

> [!CAUTION]
> ### 🛑 SON İLKE (DEĞİŞTİRİLEMEZ)
> **AI, 13 Altın Kuralın (Anayasa Bölüm 4) herhangi bir maddesine güvenilir, açıklanabilir ve istatistiksel olarak desteklenmiş bir cevap üretemiyorsa İŞLEM ÖNERİSİ VERMEYECEKTİR. Bunun yerine *"Yeterli güven düzeyi oluşmadığı için işlem önerilmiyor."* sonucunu döndürecektir.**

*(Bu yapı, projenin tek doğruluk kaynağıdır. Proje ne kadar büyürse büyüsün, geliştirilen her satır kod doğrudan bu nihai vizyona hizmet edecektir.)*
