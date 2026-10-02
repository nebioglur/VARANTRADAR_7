# V10 Kurumsal Plugin ve SDK Altyapısı

Bu klasör, VarantRadar Pro V10 Institutional Edition'ın esnek mimarisinin temelini oluşturur.

## Plugin Sistemi Nedir?
Ana çekirdek kodu değiştirmeden, sisteme dışarıdan yeni modüller eklenebilmesini sağlar.
Örneğin:
- Binance Kripto Veri Sağlayıcısı
- Matriks IQ VİOP Emir İletimi API'si
- Özel Yapay Zeka Modelleri (Örn: Sadece altın fiyatlarını tahmin eden özel model)

## Nasıl Kullanılır?
1. Yeni plugin scriptinizi `plugins/` klasörü altına ekleyin (Örn: `binance_connector.py`).
2. Plugin scriptinizde `VarantRadarPlugin` interface'ini miras alan bir sınıf tanımlayın.
3. Sistem başlangıçta `plugins` klasörünü tarayarak modülünüzü otomatik yükleyecektir.
