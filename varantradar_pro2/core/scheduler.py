import time
from typing import Dict, Any, List
import datetime

class Scheduler:
    """
    FinOS Automation & Workflow Engine (Zamanlayıcı).
    Belirli görevleri zamanı geldiğinde arka planda otonom olarak tetikler.
    Örn: 'Scheduled Scan' (Her gün saat 18:00'da radar taraması yap).
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Scheduler, cls).__new__(cls)
            cls._instance.tasks = []
        return cls._instance

    def schedule_task(self, name: str, interval_desc: str, action_type: str):
        """Sisteme yeni bir otonom görev ekler."""
        task = {
            "id": f"task_{len(self.tasks) + 1}",
            "name": name,
            "interval": interval_desc,
            "action_type": action_type,
            "status": "IDLE (Bekliyor)",
            "last_run": "Hiç çalışmadı",
            "next_run": "Bilinmiyor"
        }
        self.tasks.append(task)
        
    def trigger_task(self, task_id: str):
        """Bir görevi manuel (veya zamanı geldiğinde otonom) tetikler."""
        for t in self.tasks:
            if t["id"] == task_id:
                t["status"] = "RUNNING (Çalışıyor)"
                # Gerçek sistemde burada işlem yapılır
                time.sleep(1) # Simülasyon
                t["last_run"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                t["status"] = "COMPLETED (Tamamlandı)"
                break
                
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        return self.tasks
