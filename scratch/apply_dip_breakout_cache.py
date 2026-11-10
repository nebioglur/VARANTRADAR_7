import re

with open('services/dip_breakout_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

target1 = "CACHE_TTL = 300  # saniye"
replacement1 = """CACHE_TTL = 300  # saniye
CACHE_FILE = "dip_breakout_cache.json"

def _load_disk_cache():
    import os, json
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict) and d.get("rows"):
                with _lock:
                    _cache["rows"] = d.get("rows", [])
                    _cache["summary"] = d.get("summary", {})
                    built_str = d.get("built_at")
                    try:
                        _cache["built_at"] = datetime.fromisoformat(built_str) if built_str else datetime.now()
                    except Exception:
                        _cache["built_at"] = datetime.now()
                    _cache["error"] = None
        except Exception:
            pass

def _save_disk_cache(rows, summary, built_at):
    import json
    try:
        data = {
            "rows": rows,
            "summary": summary,
            "built_at": built_at.isoformat() if hasattr(built_at, "isoformat") else str(built_at),
            "status": "ok" if rows else "empty"
        }
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass

_load_disk_cache()"""

if target1 in text:
    text = text.replace(target1, replacement1, 1)
    print("Target 1 replaced")
else:
    print("Target 1 not found")

target2 = "def get_rows():\n    \"\"\"Cache'den satirlari dondurur; bos/bayat ise arka plan insasi tetikler.\"\"\"\n    _maybe_build()"
replacement2 = "def get_rows():\n    \"\"\"Cache'den satirlari dondurur; bos/bayat ise arka plan insasi tetikler.\"\"\"\n    with _lock:\n        if not _cache[\"rows\"]:\n            _load_disk_cache()\n    _maybe_build()"

if target2 in text:
    text = text.replace(target2, replacement2, 1)
    print("Target 2 replaced")
else:
    # Try with CRLF
    target2_crlf = target2.replace("\n", "\r\n")
    replacement2_crlf = replacement2.replace("\n", "\r\n")
    if target2_crlf in text:
        text = text.replace(target2_crlf, replacement2_crlf, 1)
        print("Target 2 CRLF replaced")
    else:
        print("Target 2 not found")

m = re.search(r'with _lock:\s+_cache\["rows"\] = rows\s+_cache\["summary"\] = summary\s+_cache\["built_at"\] = datetime\.now\(\)\s+_cache\["error"\] = [^\r\n]+', text)
if m:
    t3 = m.group(0)
    newline = "\r\n" if "\r\n" in text else "\n"
    r3 = t3 + newline + "            _save_disk_cache(rows, summary, _cache[\"built_at\"])"
    text = text.replace(t3, r3, 1)
    print("Target 3 regex replaced")
else:
    print("Target 3 not found")

with open('services/dip_breakout_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("File written")
