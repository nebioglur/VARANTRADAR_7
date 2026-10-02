import time
from typing import Dict, Any, List

from core.data_layer import UnifiedDataLayer
from engines.multi_agent_coordinator import MultiAgentCoordinator
from engines.autonomous_radar import AutonomousRadar

class FinOSKernel:
    """
    FinOS Çekirdeği (Kernel).
    Sistemin kalbidir. Modüllerin durumunu (Health), bellek kullanımını (In-Memory Simulation)
    ve işletim sisteminin başlatılmasını yönetir.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FinOSKernel, cls).__new__(cls)
            cls._instance.system_status = "OFFLINE"
            cls._instance.modules = {}
            cls._instance.data_layer = UnifiedDataLayer()
        return cls._instance

    def boot(self) -> Dict[str, Any]:
        """İşletim Sistemini Başlatır (Boot Sequence)"""
        start_time = time.time()
        
        # Modülleri 'Register' et (Kaydet)
        self.modules = {
            "Data_Layer": {"status": "ONLINE", "type": "Core"},
            "Multi_Agent_Coordinator": {"status": "ONLINE", "type": "Engine"},
            "Autonomous_Radar": {"status": "ONLINE", "type": "Engine"},
            "Smart_Money": {"status": "ONLINE", "type": "Engine"},
            "AI_Decision": {"status": "ONLINE", "type": "Engine"},
        }
        
        self.system_status = "ONLINE"
        boot_time = round(time.time() - start_time, 4)
        
        return {
            "Status": "SUCCESS",
            "Boot_Time_Sec": boot_time,
            "Active_Modules": len(self.modules)
        }
        
    def get_system_health(self) -> Dict[str, Any]:
        """Sistemin anlık sağlık (Health) ve metrik verilerini döner."""
        
        cache_size = len(self.data_layer.cache)
        
        # Basit In-Memory Memory Usage simülasyonu (Her cache item'ı için temsili 2MB)
        estimated_memory_mb = cache_size * 2.5 
        
        health_score = 100
        if estimated_memory_mb > 500: # 500 MB aşılırsa uyarı
            health_score -= 20
            
        return {
            "Kernel_Status": self.system_status,
            "System_Health_Score": health_score,
            "Memory_Usage_MB": round(estimated_memory_mb, 2),
            "Cached_Assets": cache_size,
            "Modules": self.modules
        }
