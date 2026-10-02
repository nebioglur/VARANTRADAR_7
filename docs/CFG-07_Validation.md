# CFG-07: VALIDATION
**Sistemin Doğrulama ve İspat Katmanı**

Finansal piyasalarda tek bir başarı tesadüf olabilir, kurumsallığın ölçütü "Sürdürülebilir İstatistiksel İspattır." VarantRadar Pro'nun verdiği hiçbir karar, geçmiş on yıllık veri üzerinde stres testine sokulup kanıtlanmadan (Validasyon) kullanıcıya sunulamaz.

Bu belge, AI kararlarının CFG-01 Nihai Değerlendirme Raporuna yansımadan önce geçmek zorunda olduğu test süreçlerini (Doğrulama Checklisti) tanımlar.

---

## 1. Backtest (Geriye Dönük Test)
Yapay Zekanın bulduğu "Fırsat Kurulumu", geçmiş 10 yıl içerisinde BIST (veya ilgili piyasa) üzerinde kaç kere yaşanmış ve yüzde kaçı hedef fiyata ulaşmış?
- Sonuç %50'nin altındaysa, bu kârlı bir strateji değil, bir yazı-tura oyunudur. Karar anında çöpe atılır (Discard).
- Raporlama aşamasında "Bu kurulum tarihte 482 kez yaşandı, %82.9 başarı sağladı" ibaresiyle ispat sunulur.

## 2. Walk Forward Analysis (İleri Yürüyüş Testi)
Backtest verileri bazen "Aşırı Uyumlu" (Curve Fitting / Overfitting) olabilir. Yani strateji sadece 2020 boğa piyasasında mükemmel çalışıyor ama krizde batıyor olabilir.
- **Walk Forward:** Sistem, modeli eğitirken zaman dilimlerini parçalara böler. Öğrendiği modeli görmediği bir gelecek zaman diliminde dener. Geçmişte çalışıp bugün çalışmayan ölü formasyonlar bu test sayesinde elenir.

## 3. Monte Carlo Simulation (Rassallık ve Stres Testi)
Oluşturulan yatırım planının ardışık zararlara (Losing Streak) nasıl dayanacağını simüle eder.
- Sistem, aynı stratejiyle binlerce rastgele senaryo (Farklı giriş sıraları, farklı volatilite ortamları) üretir.
- **Max Drawdown İhtimali:** En kötü ihtimalle portföyün ne kadarının eriyeceğini bulur.
- Eğer Monte Carlo simülasyonlarında "İflas Etme (Ruin)" ihtimali %1'den bile büyükse, Trade Quality skoru anında düşürülür.

## 4. Accuracy & Drift Monitoring (Doğruluk ve Sapma İzlemi)
Yapay zeka modellerinin canlı piyasadaki performansları geriye dönük (örneğin son 3 ay) olarak sürekli ölçülür.
- Eğer bir indikatör kümesi veya karar motoru eskisi kadar doğru sonuç vermemeye başlarsa (Model Drift), sistem otonom olarak o modelin karar ağırlığını (Weight) düşürür.

## 5. Explainable AI (Açıklanabilirlik ve Mantık Testi)
Sistem tamamen "Kara Kutu" olamaz. Makine öğrenimi algoritmasının bir ağırlığı (Örn: "Bugün MACD yerine F/K oranını %70 dikkate alıyorum") neden değiştirdiği açıklanabilmelidir.
- Doğrulama katmanı, yapay zekadan aldığı her karar için bir "Karar Ağacı İzlemi (Decision Tree Trace)" tutar. Olası bir sistem hatasında, hangi motorun yanlış veri ürettiği şeffafça tespit edilebilir.
