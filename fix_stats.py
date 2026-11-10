# -*- coding: utf-8 -*-
with open("server.py", "r", encoding="utf-8") as f:
    code = f.read()

bad_server = """        if today_str not in audits:
            cached_candidates = GLOBAL_DASHBOARD_CACHE.get("tavan_adaylari", [])
            cached_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
            if cached_candidates and cached_stats:
                TavanAuditTracker.record_snapshot(
                    cached_candidates,
                    all_symbols_stats=cached_stats,
                    date_str=today_str,
                )
                TavanAuditTracker.update_daily_progress(
                    cached_stats,
                    date_str=today_str,
                )"""
good_server = """        if today_str not in audits:
            cached_candidates = GLOBAL_DASHBOARD_CACHE.get("tavan_adaylari", [])
            cached_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
            if cached_stats:
                TavanAuditTracker.record_snapshot(
                    cached_candidates,
                    all_symbols_stats=cached_stats,
                    date_str=today_str,
                )
                TavanAuditTracker.update_daily_progress(
                    cached_stats,
                    date_str=today_str,
                )"""
code = code.replace(bad_server, good_server)
with open("server.py", "w", encoding="utf-8") as f:
    f.write(code)

with open("services/tavan_tracker.py", "r", encoding="utf-8") as f:
    code = f.read()
bad_tavan = """        if not tavan_candidates:
            return {}"""
good_tavan = """        if tavan_candidates is None:
            return {}"""
code = code.replace(bad_tavan, good_tavan)
with open("services/tavan_tracker.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Patched stats tracking.")
