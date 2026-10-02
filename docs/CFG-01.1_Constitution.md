# CFG-01.1: VARANTRADAR ANAYASASI
**Değiştirilemez 11 Altın Kural (The 11 Golden Rules)**

Bu anayasa, VarantRadar Pro ekosistemine eklenecek olan her kod satırının, her yeni yapay zeka modelinin ve her yeni indikatörün uymak zorunda olduğu mutlak sınırlar bütünüdür. Hiçbir algoritma bu kuralları ihlal edemez.

### KURAL 1: Çıktı Sinyal Değil, Rapordur
Sistem kullanıcısına asla izole bir "AL" veya "SAT" kelimesi sunamaz. Nihai ürün daima *AI Investment Evaluation Standard (CFG-01)* kurallarına uygun, ölçülebilir ve istatistiksel bir Karar Destek Raporudur. İndikatörler sadece bu raporun ham maddesidir.

### KURAL 2: Sermaye Koruması (Capital Preservation) İlk Görevdir
Fırsat kaçırmak sistemsel bir hata değildir, ancak sermaye kaybetmek (riskleri görmezden gelmek) affedilemez bir hatadır. Sistem, getiri potansiyelinden önce her zaman "Maksimum Kayıp (Drawdown)" ihtimalini hesaplar. Riske atılan 1 birime karşılık en az 2 birim getiri (Risk/Getiri oranı < 1:2) yoksa, sistem işlemi otomatik olarak "Önerilmez" statüsüne çeker.

### KURAL 3: İstatistiksel Kanıt Zorunluluğu
"Hissiyat" veya "Tahmin" algoritmalarda yer almaz. Bir setup (formasyon/durum) başarılı ilan edilecekse, sistem bunu geçmişte en az yüzlerce kez benzer piyasa koşulunda test etmiş (Backtest & Monte Carlo) ve istatistiksel bir başarı yüzdesi (%X) çıkarmış olmalıdır. Kanıtlanmayan kural, kural değildir.

### KURAL 4: Açıklanabilir Yapay Zeka (Explainable AI)
AI'nin aldığı her karar, bir insanın (fon yöneticisinin) okuyup anlayabileceği şekilde açıklanabilmelidir. "Kara Kutu (Black Box)" yaklaşımı yasaktır. Kullanıcı "Sistem neden AL dedi?" diye sorduğunda, ardındaki faktörler (Temel, Teknik, Makro) açıkça listelenebilmelidir.

### KURAL 5: Şeytanın Avukatı (Counter Opinion)
Güven skoru %99 bile olsa, sistem kendi verdiği her karara karşı "Bu işlem neden ters gidebilir?" sorusunu sorarak bir karşıt görüş (Counter Opinion) veya İptal Şartı (Geçersizlik Koşulu) üretmek zorundadır.

### KURAL 6: Çoklu Periyot ve Çoklu Ekosistem Doğrulaması
Sadece tek bir zaman dilimine (Timeframe) veya tek bir veriye (Sadece Teknik) bakarak karar alınamaz. İşlem günlük periyotta veriliyorsa, haftalık ve aylık ana trendler kontrol edilmeli; teknik analiz veriliyorsa, şirketin temel (Bilanço) ve makro piyasa rejimi (Boğa/Ayı) mutlaka ağırlıklandırmaya katılmalıdır.

### KURAL 7: Puanlama (Confidence Index) Ölçeklenebilirliği
Sistemin ürettiği tüm metrikler 0 ile 100 arasında normalize edilir. Hiçbir modül diğerine karşı mutlak üstünlüğe sahip değildir (Orchestration). Nihai Karar (Executive Decision), tüm bu alt skorların önceden belirlenmiş ağırlıklarına göre hesaplanmış saf matematiğidir.

### KURAL 8: Stop-Loss (Zarar Kes) Mutlakiyettir
Sistem, girmeyi planladığı her işlemin nerede "Geçersiz" (Invalidation Point) olacağını işlemden önce belirler. Kullanıcıya hedef fiyattan (TP) önce daima Stop-Loss noktası sunulur ve bu nokta bilimsel (Örn: ATR, Önceki Dip) bir zemine dayanmalıdır.

### KURAL 9: Smart Money (Akıllı Para) Takibi
Teknik indikatörler fiyatı, fiyat ise kurumsal parayı izler. Hacim ve likidite anomalileri (Blok alışlar, algoritmik bot hareketleri), fiyat hareketinden daha önce gerçekleştiği için sistem analizlerinde önceliğe (Weight) sahiptir. 

### KURAL 10: Hata Töleransı ve Veri Koruması (Fault Tolerance)
Bilanço verisi geciktiğinde, makro endeks çöktüğünde veya haber akışı kesildiğinde VarantRadar Pro çökmez. Eksik veriyi tespit eder, kullanıcıyı uyarır ve elindeki mevcut sağlam verilerle risk skorunu yükselterek karar üretmeye devam eder.

### KURAL 11: Ölçeklenebilirlik (Enterprise Modularity)
Sistem donuk bir yazılım değildir. Yarın VİOP, Kripto veya Tahvil piyasaları eklendiğinde, çekirdek mimariyi (Kernel) bozmadan bir eklenti (Plugin) gibi sisteme entegre edilebilecek modüler bir yapı korunmak zorundadır.
