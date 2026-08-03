# CFG-03: DATA ARCHITECTURE
**Sistemin Veri Katmanı ve Akış Standartları**

Yapay zeka modellerinin kalitesi, içine giren verinin kalitesiyle doğrudan orantılıdır ("Garbage In, Garbage Out"). VarantRadar Pro, perakende seviyesi veri kullanımını reddeder; bunun yerine kurumsal seviyede, doğrulanmış ve otonom bir "Unified Data Layer" (Birleşik Veri Katmanı) mimarisi kullanır.

Bu belge, verinin kaynağını, sisteme gelişini ve hafızada nasıl tutulacağını standartlaştırır.

---

## 1. Veri Kaynakları (Data Sources)
Sistem asla tek bir veri kaynağına bağımlı (Single Point of Failure) olamaz.
- **Birincil Veri (Primary):** Fiyat, Hacim ve Teknik Veriler (Örn: Yahoo Finance, Matriks, BIST API).
- **Temel Veri (Fundamental):** Şirket bilançoları, Çarpanlar ve KAP duyuruları (Örn: İş Yatırım, Fintables veya yfinance fundamental).
- **Alternatif Veri (Alt-Data):** Haber akışı, Sosyal Medya duyarlılığı (Sentiment) ve Makroekonomik takvimler.
- *Kural:* Bir veri kaynağı çöktüğünde veya gecikme yaşadığında, sistem otonom olarak ikincil (Fallback) veri sağlayıcısına geçmek zorundadır.

## 2. Veri Akışı (Data Pipeline / Flow)
Ham veri asla doğrudan Yapay Zeka Karar Motoruna gönderilmez. Veri şu boru hattından (Pipeline) geçer:
1. **Fetch (Çekme):** Veri dış API'den çekilir.
2. **Cleanse (Temizleme):** Boş değerler (NaN), sıfıra bölünme hataları ve "Outlier" (Anomali) fiyat hareketleri (örn: veritabanı hatası kaynaklı %900 düşüş) filtrelenir.
3. **Normalize (Standardizasyon):** 1 dakikalık, 5 dakikalık ve Günlük veriler ortak bir zaman damgasıyla (Time-Series Alignment) hizalanır.
4. **Deliver (Teslimat):** İşlenmiş veri, analiz motorlarına sunulur.

## 3. In-Memory Cache (Önbellekleme)
Otonom bir radar motoru binlerce hisseyi saniyeler içinde tarayamaz, çünkü sürekli API isteği yapmak sistemi kitler (Rate Limit).
- **Çözüm:** Sisteme çekilen her veri anında In-Memory Cache (Bellek) içerisine kaydedilir. 
- Eğer Risk Motoru, Teknik Analiz Motorunun az önce çektiği TUPRS verisini isterse; sistem internete çıkmaz, veriyi mikrosaniyeler içinde Cache'den (Bellekten) teslim eder.
- Bu yaklaşım sistemin Wall Street hızında, gecikmesiz (Ultra-Low Latency) çalışmasını sağlar.

## 4. Live Data & Streaming (Canlı Veri)
Gün içi (Intraday) işlemlerde zaman gecikmesi (Lag) kabul edilemez.
- Sistem sadece geçmiş (Historical) kapanış verileriyle çalışmakla kalmaz; aracı kurum WebSocket'leri üzerinden akan "Tick by Tick" (Anlık İşlem) verisini yakalayabilen, canlı derinlik ve kademe analizi yapabilen asenkron bir dinleme yeteneğine sahiptir.

## 5. Veri Doğrulama ve Kalite (Data Validation & Quality)
Analiz başlamadan önce gelen veri "Quality Gate" (Kalite Kapısı) testinden geçer:
- **Eksik Veri Kontrolü:** Son 100 mumun 5'i eksikse, sistem bunu "Bozuk Veri" ilan eder ve işlem planlamasını reddeder.
- **Feature Drift:** Verinin istatistiksel dağılımında aniden devasa bir değişim olursa (Örn: Sermaye artırımı/Bölünme verisi fiyatlara yansımamışsa), sistem bunu anomali olarak etiketler (Alert Center'a bildirir) ve analizi otonom olarak durdurur.
