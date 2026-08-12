import sys

with open('services/tavan_tracker.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace get_audit_report cumulative logic
old_audit_logic = """        for d_key, aud in all_audits.items():
            summ = aud.get("summary", {})
            t_cnt = summ.get("total_candidates", 0)
            if t_cnt > 0:
                cum_total += t_cnt
                cum_tavan += summ.get("hit_ceiling_count", 0)
                cum_plus5 += summ.get("hit_plus5_count", 0)
                cum_max_gains.append(summ.get("avg_max_gain_pct", 0.0))"""

new_audit_logic = """        from datetime import datetime
        for d_key, aud in all_audits.items():
            try:
                if datetime.strptime(d_key, "%Y-%m-%d").weekday() >= 5:
                    continue
            except Exception:
                pass
            
            summ = aud.get("summary", {})
            t_cnt = summ.get("total_candidates", 0)
            if t_cnt > 0:
                cum_total += t_cnt
                cum_tavan += summ.get("hit_ceiling_count", 0)
                cum_plus5 += summ.get("hit_plus5_count", 0)
                cum_max_gains.append(summ.get("avg_max_gain_pct", 0.0))"""

if old_audit_logic in content:
    content = content.replace(old_audit_logic, new_audit_logic)
else:
    print('Failed to replace old_audit_logic')

# Replace get_long_term_history filtering logic
old_hist_logic = """        # Tarih filtreleme
        filtered_audits = {}
        for d, aud in all_audits.items():
            if start_date and d < start_date:
                continue
            if end_date and d > end_date:
                continue
            filtered_audits[d] = aud

        if not filtered_audits:
            filtered_audits = all_audits"""

new_hist_logic = """        from datetime import datetime
        # Tarih filtreleme
        filtered_audits = {}
        for d, aud in all_audits.items():
            try:
                if datetime.strptime(d, "%Y-%m-%d").weekday() >= 5:
                    continue
            except Exception:
                pass
                
            if start_date and start_date.strip():
                if d < start_date:
                    continue
            if end_date and end_date.strip():
                if d > end_date:
                    continue
            filtered_audits[d] = aud"""

if old_hist_logic in content:
    content = content.replace(old_hist_logic, new_hist_logic)
else:
    print('Failed to replace old_hist_logic')

with open('services/tavan_tracker.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('SUCCESS')
