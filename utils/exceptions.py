"""
VarantRadar Pro - Özel Hata Sınıfları
"""

class VarantRadarError(Exception):
    """Ana hata sınıfı"""
    pass

class DataFetchError(VarantRadarError):
    """Veri indirme sırasında oluşan hatalar"""
    pass

class CalculationError(VarantRadarError):
    """İndikatör veya formasyon hesaplamaları sırasındaki hatalar"""
    pass

class DatabaseError(VarantRadarError):
    """Veritabanı okuma/yazma hataları"""
    pass
