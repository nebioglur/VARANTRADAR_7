# CFG-10: AUTONOMOUS AI TRADER
**Nihai Hedef: Uçtan Uca Otonom Yatırım Operasyonu**

Onlarca mimari belge, yazılan yüzlerce motor, konulan katı anayasa kuralları (CFG-01.1) ve doğrulama süreçleri (CFG-07)... Tüm bunların hizmet ettiği tek bir "Kutsal Kase" (Holy Grail) vardır: **İnsan faktörünün, duygunun ve yorgunluğun sıfıra indirildiği Tam Otonom İşlem Katmanı.**

Bu belge, VarantRadar Pro'nun sadece bir "Karar Destek" raporlayıcısı olmaktan çıkıp, o kararı piyasaya bizzat "Emir (Order)" olarak ileten bir operasyon merkezine dönüşmesini standartlaştırır.

---

## 1. Enterprise Trading & Execution Platform (Aracı Kurum Entegrasyonu)
Rapor (CFG-01) üretilip "Trade Quality: A+" sonucu çıktığında, sistem kullanıcıdan bağımsız olarak (veyahut kullanıcının sadece tek tuşla onaylamasıyla) harekete geçer.
- **OMS (Order Management System):** Seçilen aracı kurumun (Örn: İş Yatırım, Binance, Interactive Brokers) API'sine bağlanılır.
- Sistem CFG-06 (Trade Planner) belgesinde hesapladığı o "Optimal Kademeli Alım" ve "Stop-Loss" emirlerini saniyesi saniyesine borsanın tahtasına iletir.

## 2. Smart Order Routing (Akıllı Emir Yönlendirme)
Yüklü miktarda alım/satım yapıldığında piyasada "Slippage (Fiyat Kayması)" oluşur ve kurumlar uyanır.
- Sistem bunu engellemek için emirleri devasa bloklar (Örn: 1 Milyon Lot) halinde tahtaya göndermez. Iceberg (Buzdağı) veya TWAP/VWAP algoritmaları kullanarak emirleri gün içine parçalar halinde yayar ve varlığını Smart Money'den gizler.

## 3. Post-Trade Lifecycle (İşlem Sonrası Yönetim)
Alım yapıldıktan sonra sistem o hisseyi unutmaz, aksine asıl mesai o an başlar.
- Otonom trader saniye saniye hissenin tiklerini (Tick data) okur.
- Fiyat yükseldikçe, CFG-06'da belirlenen "Trailing Stop" seviyesini borsadaki emre yansıtarak kârı fiziksel olarak kilitler.
- Herhangi bir "Invalidation (Geçersizlik)" durumu oluşursa (Örn: CEO istifa haberi düştü), sistem beklemeden saniyeler içinde "Piyasa Fiyatından Sat (Market Sell)" emri göndererek portföyü nakde kaçırır.

## ZİRVE (SONUÇ)
VarantRadar Pro, **CFG-00 Manifesto** belgesiyle yola bir isyan olarak çıkmış, **CFG-01 Anayasa** belgesiyle kendi ahlakını yazmış, **Core, Data ve Analysis** belgeleriyle kaslarını inşa etmiş, **Decision** belgesiyle beynini yaratmış ve en nihayetinde bu **CFG-10 Autonomous Trader** vizyonuyla "Kendi Başına Yaşayan, Düşünen ve Ticaret Yapan Bir Finansal Organizmaya" dönüşmüştür.
