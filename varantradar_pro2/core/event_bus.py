from typing import Callable, Dict, List, Any
import time

class EventBus:
    """
    CFG-02 Core Architecture: Event-Driven Architecture
    Sistemdeki modüllerin birbirine doğrudan bağlanmadan (decoupled)
    haberleşmesini sağlayan Olay Yöneticisi.
    """
    _subscribers: Dict[str, List[Callable]] = {}
    _event_history: List[Dict[str, Any]] = []

    @classmethod
    def subscribe(cls, event_type: str, callback: Callable):
        """Bir olayı (Event) dinlemek için kayıt olur."""
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(callback)

    @classmethod
    def publish(cls, event_type: str, payload: Any):
        """Sisteme yeni bir olay (Event) fırlatır."""
        event_record = {
            "timestamp": time.time(),
            "type": event_type,
            "payload": payload
        }
        cls._event_history.append(event_record)
        
        # Dinleyicilere haber ver (Asenkron simülasyonu)
        if event_type in cls._subscribers:
            for callback in cls._subscribers[event_type]:
                try:
                    callback(payload)
                except Exception as e:
                    # Hata töleransı: Bir dinleyici çökse bile Event Bus çökmeyecek (CFG-01.1 Kural 10)
                    print(f"[EVENT BUS ERROR] Listener {callback.__name__} failed on event {event_type}: {e}")

    @classmethod
    def get_history(cls) -> List[Dict[str, Any]]:
        return cls._event_history
