import time
from typing import List, Dict
from data.providers.base_provider import BaseDataProvider

class DataHealthMonitor:
    """
    CFG-03.1 — DATA HEALTH MONITOR
    Tüm provider'ların sağlık durumunu sürekli izler ve raporlar.
    
    İzlenen Metrikler:
    - API gecikmesi (Latency)
    - Error Rate
    - Success Rate
    - Uptime
    - Son başarılı veri zamanı
    """
    
    def __init__(self):
        self._providers: List[BaseDataProvider] = []
        self._alerts: List[Dict] = []
    
    def register_provider(self, provider: BaseDataProvider):
        """Yeni bir provider'ı izleme listesine ekler."""
        self._providers.append(provider)
    
    def get_all_health(self) -> List[Dict]:
        """Tüm provider'ların sağlık raporunu döner."""
        reports = []
        for p in self._providers:
            health = p.health_check()
            reports.append(health)
        return sorted(reports, key=lambda x: x["priority"])
    
    def get_best_provider(self) -> BaseDataProvider:
        """En sağlıklı ve en yüksek öncelikli provider'ı döner."""
        available = []
        for p in self._providers:
            h = p.health_check()
            if h["status"] != "DOWN":
                available.append((p, h))
        
        if not available:
            # Hepsi DOWN ise ilk provider'ı (primary) döndür
            return self._providers[0] if self._providers else None
        
        # Önce priority'ye, sonra success_rate'e göre sırala
        available.sort(key=lambda x: (x[1]["priority"], -x[1]["success_rate"]))
        return available[0][0]
    
    def generate_dashboard_report(self) -> Dict:
        """Arayüze gönderilecek sağlık dashboard verisi."""
        reports = self.get_all_health()
        
        all_up = all(r["status"] == "UP" for r in reports)
        any_down = any(r["status"] == "DOWN" for r in reports)
        
        return {
            "overall_status": "HEALTHY" if all_up else ("CRITICAL" if any_down else "DEGRADED"),
            "provider_count": len(reports),
            "providers": reports,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
