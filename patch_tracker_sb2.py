# -*- coding: utf-8 -*-
with open('services/tavan_tracker.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Fallback in _ensure_dir'i silebiliriz cunku artik ensure dir'e gerek yok
old_ens = '''    @classmethod
    def _ensure_dir(cls):
        try:
            os.makedirs(os.path.dirname(AUDIT_FILE_PATH), exist_ok=True)
        except Exception:
            pass'''
new_ens = '''    @classmethod
    def _ensure_dir(cls):
        pass'''
content = content.replace(old_ens, new_ens)

old_load_start = '''    @classmethod
    def load_all_audits(cls) -> Dict[str, Any]:
        cls._ensure_dir()
        if os.path.exists(AUDIT_FILE_PATH):
            try:
                with open(AUDIT_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)'''
new_load_start = '''    _memory_cache = None
    @classmethod
    def load_all_audits(cls) -> Dict[str, Any]:
        if cls._memory_cache: return cls._memory_cache
        try:
            from services.supabase_client import get_kv
            sb_data = get_kv("tavan_audits", "all_audits", None)
            if sb_data and isinstance(sb_data, dict) and len(sb_data) > 0:
                cls._memory_cache = sb_data
                return sb_data
        except Exception as e:
            print(f"[TavanAuditTracker] Supabase yukleme hatasi: {e}")
        
        cls._ensure_dir()
        if os.path.exists(AUDIT_FILE_PATH):
            try:
                with open(AUDIT_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)'''
content = content.replace(old_load_start, new_load_start)

old_save_start = '''    @classmethod
    def save_all_audits(cls, data: Dict[str, Any]):
        cls._ensure_dir()
        try:
            with open(AUDIT_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[TavanTracker] Dosyaya yazilamadi (Izin hatasi): {e}")'''
new_save_start = '''    @classmethod
    def save_all_audits(cls, data: Dict[str, Any]):
        cls._memory_cache = data
        try:
            from services.supabase_client import set_kv
            set_kv("tavan_audits", "all_audits", data)
        except Exception as e:
            print(f"[TavanTracker] Supabase yazma hatasi: {e}")'''
content = content.replace(old_save_start, new_save_start)

with open('services/tavan_tracker.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("PATCH_TRACKER_OK2")
