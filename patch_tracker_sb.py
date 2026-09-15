# -*- coding: utf-8 -*-
with open('services/tavan_tracker.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

old_load = r'''    @classmethod
    def load_all_audits\(cls\) -> Dict\[str, Any\]:
        cls\._ensure_dir\(\)
        if os\.path\.exists\(AUDIT_FILE_PATH\):
            try:
                with open\(AUDIT_FILE_PATH, "r", encoding="utf-8"\) as f:
                    data = json\.load\(f\)
                    if data and isinstance\(data, dict\) and len\(data\) > 0:
                        return data
            except Exception as e:
                print\(f"\[TavanAuditTracker\] Yukleme hatasi: \{e\}"\)
        
        # Hen\z seans kayd\ yoksa 04 A\ustos 2026 ba\lang\ verilerini y\kle ve kaydet
        initial = cls\._generate_initial_historical_data\(\)
        cls\.save_all_audits\(initial\)
        return initial'''

new_load = '''    _memory_cache = None

    @classmethod
    def load_all_audits(cls) -> Dict[str, Any]:
        try:
            from services.supabase_client import get_kv
            sb_data = get_kv("tavan_audits", "all_audits", None)
            if sb_data and isinstance(sb_data, dict) and len(sb_data) > 0:
                cls._memory_cache = sb_data
                return sb_data
        except Exception as e:
            print(f"[TavanAuditTracker] Supabase yukleme hatasi: {e}")
            
        if cls._memory_cache:
            return cls._memory_cache

        initial = cls._generate_initial_historical_data()
        cls.save_all_audits(initial)
        cls._memory_cache = initial
        return initial'''
content = re.sub(old_load, new_load, content)

old_save = r'''    @classmethod
    def save_all_audits\(cls, data: Dict\[str, Any\]\):
        cls\._ensure_dir\(\)
        try:
            with open\(AUDIT_FILE_PATH, "w", encoding="utf-8"\) as f:
                json\.dump\(data, f, indent=4, ensure_ascii=False\)
        except Exception as e:
            print\(f"\[TavanTracker\] Dosyaya yazilamadi \(Izin hatasi\): \{e\}"\)'''

new_save = '''    @classmethod
    def save_all_audits(cls, data: Dict[str, Any]):
        cls._memory_cache = data
        try:
            from services.supabase_client import set_kv
            set_kv("tavan_audits", "all_audits", data)
        except Exception as e:
            print(f"[TavanTracker] Supabase yazma hatasi: {e}")'''
content = re.sub(old_save, new_save, content)

with open('services/tavan_tracker.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("PATCH_TRACKER_OK")
