# CFG-06: TRADE PLANNER
**Otonom İşlem ve Risk Planlayıcısı**

VarantRadar Pro, bir yatırımın "İyi" olduğuna karar verdikten (CFG-05 Decision) sonra onu sokağa başıboş bırakmaz. Başarılı bir yatırımın sırrı iyi bir sinyal değil, kusursuz bir risk yönetimi ve çıkış planıdır. 

Bu belge, AI tarafından onaylanan bir işlemin "Nasıl oynanacağını" tanımlayan askeri bir operasyon planıdır. Her değerlendirme raporu (CFG-01) bu plana uygun bir strateji haritası içermek zorundadır.

---

## 1. Giriş Stratejisi (Entry Execution)
Algoritma "Piyasa fiyatından (Market Order) al" demek yerine, akıllı para (Smart Money) gibi kademeli giriş planı yapar.
- **Optimal Entry:** İşleme girmek için en uygun fiyat aralığı.
- **Kademeli Alım (Scaling In):** Tüm sermayeyi tek bir fiyattan riske atmak yerine, destek seviyelerine dağıtılmış parçalı alım (DCA) noktaları üretilir.

## 2. Zarar Kes (Stop-Loss) ve Sermaye Koruması
VarantRadar Anayasası'nın (CFG-01.1) 8. kuralı gereği Stop-Loss esnetilemez.
- **Invalidation Point (Geçersizlik Noktası):** AI'nin "Bu fiyatın altını görürsek benim teorim çökmüştür" dediği, matematiksel (Örn: ATR veya önceki dip) çıkış seviyesi.
- **Trailing Stop (İzleyen Stop):** Fiyat hedefe doğru ilerledikçe, algoritma kârı kilitlemek için Stop seviyesini otonom olarak yukarı çeker.

## 3. Kar Alma Stratejisi (Take Profit - TP)
Açgözlülüğü engellemek için çıkış noktaları da kademeli olarak planlanır.
- **TP 1 (Kısa Vade):** İşlemin riskini sıfırlamak için %X'lik kısmın satılacağı ilk güvenli liman.
- **TP 2 (Ana Hedef):** Olasılık matrisinin işaret ettiği ana değerleme noktası.
- **TP 3 (Momentum Sürüşü):** Eğer trend çok güçlüyse (Örn: RSI aşırı alımda kalmaya devam ediyorsa), işlemin son çeyreğinin "Gittiği yere kadar" (Trailing Stop ile) taşınacağı seviye.

## 4. Pozisyon Büyüklüğü (Position Sizing) & Risk Yönetimi
Sistem, portföy yöneticisi rolü oynar.
- **Maksimum Risk:** Tek bir işlemde toplam sermayenin %1 veya %2'sinden fazlasının (Stop-Loss olması durumunda dahi) kaybedilmesini engelleyecek optimal lot/kontrat miktarını (Position Size) hesaplar.
- **Risk/Getiri (R:R):** Hedeflenen kârın (TP2) ile alınan riskin (Stop Loss) oranı. CFG-01.1 Kural 2 gereği bu oran her zaman > 1:2 olmak zorundadır.

## 5. Süre ve Olasılık Beklentisi (Duration & Time-to-Target)
Zaman da sermaye kadar değerlidir. 
- Algoritma sadece fiyatı değil, zamanı da tahmin eder: *"Tarihsel verilere göre bu formasyonun TP2'ye ulaşması ortalama 6.2 işlem günü sürmektedir."*
- Eğer belirlenen süre (Örn: 10 gün) aşılırsa ve fiyat hala yataysa, sistem zaman israfını (Time Decay / Opportunity Cost) önlemek için işlemden "Süre Aşımı" (Time Stop) sebebiyle çıkış (Exit) önerebilir.
