class InsufficientConfidenceError(Exception):
    """
    VARANTRADAR PRO - SON İLKE (DEĞİŞTİRİLEMEZ) KURALI
    
    Yapay zeka (Executive Engine) yeterli istatistiksel ispatı, 
    risk yönetimini veya temel güven skorunu sağlayamazsa bu hata fırlatılır.
    Sistemin asılsız işlem üretmesini kökünden engeller.
    """
    def __init__(self, message: str, confidence_score: float = None, risk_status: str = None):
        self.confidence_score = confidence_score
        self.risk_status = risk_status
        super().__init__(f"İŞLEM REDDEDİLDİ: {message} (Güven: {confidence_score}, Risk: {risk_status})")
