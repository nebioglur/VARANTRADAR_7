# CFG-08: AI LEARNING
**Yapay Zeka Öğrenim ve Öz-Gelişim Döngüsü (Continuous Learning)**

Durağan bir yapay zeka, finansal piyasaların sürekli değişen yapısında (Market Evolution) eninde sonunda iflas eder. VarantRadar Pro'nun beyni, dışarıdan sürekli kod yazılmasına ihtiyaç duymadan, hatalarından ve başarılarından ders çıkaran (Machine Learning Lifecycle) otonom bir "Öğrenme Döngüsüne" sahiptir.

Bu belge, sistemin kendi kendini nasıl eğiteceğini ve geliştireceğini tanımlar.

---

## 1. Feedback Loop (Geri Bildirim Döngüsü)
Sistemin CFG-01 formatında ürettiği her "Nihai Karar", veritabanına bir "Tahmin Logu" olarak kaydedilir.
- İşlem süresi dolduğunda (Örn: 6 gün sonra), sistem otonom olarak geriye döner ve *"Tahminim tuttu mu?"* diye kontrol eder.
- **Başarılıysa:** O kararı verdiren motorların (Örn: Trend Motoru ve Smart Money Motoru) sistem içindeki "Güvenilirlik Ağırlığı" küçük bir miktar artırılır.
- **Başarısızsa (Stop Olmuşsa):** Sisteme kayıp yaşatan ağırlıklar cezalandırılır. Algoritma *"Bu kaybın sebebi hatalı bilanço verisi miydi, yoksa sahte bir breakout muydu?"* sorusunu sorarak hatanın kaynağını (Root Cause Analysis) bulur.

## 2. Model Drift Detection (Model Sapması Tespiti)
Piyasaların doğası değişebilir (Örn: Eskiden işe yarayan bir RSI stratejisi algoritmik botlar yüzünden artık çalışmıyor olabilir).
- Sistem, kendi başarı oranını (Hit Rate) 30 günlük hareketli ortalamalarla takip eder.
- Eğer başarı oranı istatistiksel olarak anlamlı bir düşüş (Drift) yaşarsa, AI mevcut ağırlık tablosunu askıya alır ve "Gözden Geçirme Moduna (Review Mode)" geçer. Karar üretmeyi (Rapor basmayı) geçici olarak yavaşlatır veya durdurur.

## 3. Auto-Feature Discovery (Otonom Faktör Keşfi)
Gelişmiş AI versiyonlarında, sistem sadece bizim verdiğimiz indikatörlerle (MACD, RSI) yetinmez.
- Kendi içindeki Deep Learning (Derin Öğrenme) katmanı sayesinde, ham fiyat ve hacim verileri üzerinden insanların göremediği "Gizli Matematiksel Örüntüleri" keşfeder ve bunları yeni bir "Custom Indicator" olarak kendi analiz kaslarına ekler.
