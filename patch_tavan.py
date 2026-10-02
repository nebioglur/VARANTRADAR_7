# -*- coding: utf-8 -*-
with open('services/tavan_tracker.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Fallback in _ensure_dir
old_ens = r'''    def _ensure_dir\(cls\):
        os\.makedirs\(os\.path\.dirname\(AUDIT_FILE_PATH\), exist_ok=True\)'''
new_ens = '''    def _ensure_dir(cls):
        try:
            os.makedirs(os.path.dirname(AUDIT_FILE_PATH), exist_ok=True)
        except Exception:
            pass'''
content = re.sub(old_ens, new_ens, content)

# Fallback in save_all_audits
old_save = r'''    def save_all_audits\(cls, data: Dict\[str, Any\]\):
        cls\._ensure_dir\(\)
        with open\(AUDIT_FILE_PATH, "w", encoding="utf-8"\) as f:
            json\.dump\(data, f, indent=4, ensure_ascii=False\)'''
new_save = '''    def save_all_audits(cls, data: Dict[str, Any]):
        cls._ensure_dir()
        try:
            with open(AUDIT_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[TavanTracker] Dosyaya yazilamadi (Izin hatasi): {e}")'''
content = re.sub(old_save, new_save, content)

with open('services/tavan_tracker.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("TAVAN_FALLBACK_OK")
