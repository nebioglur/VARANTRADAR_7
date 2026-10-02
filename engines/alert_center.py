from core.event_bus import EventBus
from typing import List, Dict, Any

class AlertCenter:
    """
    FinOS Alert Center (Alarm Merkezi).
    Event Bus üzerinden geçen ve içinde 'ALERT' kelimesi bulunan tüm acil durum sinyallerini
    (Örn: CRITICAL_NEWS_ALERT, MANIPULATION_ALERT) yakalayıp saklar.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AlertCenter, cls).__new__(cls)
            cls._instance.active_alerts = []
            
            # FinOS Event Bus'a bağlan ve Alert'leri dinle
            eb = EventBus()
            # Şimdilik basitçe tüm olayları dinleyip ALERT olanları filtreleyeceğiz
            # (İdealde regex veya specific event subscription yapılır)
        return cls._instance

    def fetch_alerts(self) -> List[Dict[str, Any]]:
        """Event Bus'tan ALERT tipi olayları çeker."""
        eb = EventBus()
        all_events = eb.get_recent_events()
        
        # İçinde ALERT kelimesi geçen olayları filtrele
        alerts = [e for e in all_events if "ALERT" in e["type"]]
        return alerts
        
    def clear_alerts(self):
        # Event bus geçmişini silmek istemeyiz, bu yüzden sadece okuma yapıyoruz.
        pass
