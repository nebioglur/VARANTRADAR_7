import os
import json
import time
from typing import Dict, Any

class AuditEngine:
    """
    CFG-03.1 — AUDIT ENGINE
    
    Veri güvenliği ve izlenebilirlik kuralları gereği, sistemin yaptığı 
    tüm veri çekme, failover ve analiz ret işlemlerini loglar.
    """
    
    def __init__(self):
        self._audit_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "logs", 
            "audit"
        )
        os.makedirs(self._audit_dir, exist_ok=True)
        
        # Günlük bazda log dosyası
        self._current_date = time.strftime("%Y%m%d")
        self._log_file = os.path.join(self._audit_dir, f"audit_{self._current_date}.jsonl")
        
    def _rotate_log_if_needed(self):
        date = time.strftime("%Y%m%d")
        if date != self._current_date:
            self._current_date = date
            self._log_file = os.path.join(self._audit_dir, f"audit_{self._current_date}.jsonl")
            
    def log_event(self, event_type: str, symbol: str, details: Dict[str, Any]):
        """
        Örnek Event Tipleri: 
        - DATA_FETCH_SUCCESS
        - FAILOVER_TRIGGERED
        - VALIDATION_FAILED
        - SAFE_MODE_ACTIVATED
        """
        self._rotate_log_if_needed()
        
        entry = {
            "timestamp": time.time(),
            "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": event_type,
            "symbol": symbol,
            "details": details
        }
        
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[AuditEngine] Log yazılamadı: {e}")

# Singleton instance
Auditor = AuditEngine()
