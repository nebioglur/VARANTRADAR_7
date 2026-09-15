import sys
import math

with open('services/tavan_tracker.py', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to import math if not imported, but let's just use a simple string replace for the calculations
old_calc = '''                    c_pct = ((c_price - m_price) / p_close) * 100
                    m_pct = ((h_price - m_price) / p_close) * 100'''

new_calc = '''                    import math
                    c_pct = ((c_price - m_price) / p_close) * 100
                    m_pct = ((h_price - m_price) / p_close) * 100
                    if math.isnan(c_pct): c_pct = 0.0
                    if math.isnan(m_pct): m_pct = 0.0'''

if old_calc in content:
    content = content.replace(old_calc, new_calc)

# Also fix api_chart_data in server.py which is throwing NaN for ema21
with open('server.py', 'r', encoding='utf-8') as f:
    server_content = f.read()
    
# In server.py, we have `sanitize_for_json` already defined. 
# Let's make sure `/api/chart_data` uses it!
# Wait, /api/chart_data returns jsonify(data), but doesn't sanitize?
import re
server_content = re.sub(r'return jsonify\(chart_data\)', r'return jsonify(sanitize_for_json(chart_data))', server_content)
server_content = re.sub(r'return jsonify\(\{"status": "success", "data": chart_data\}\)', r'return jsonify({"status": "success", "data": sanitize_for_json(chart_data)})', server_content)

with open('services/tavan_tracker.py', 'w', encoding='utf-8') as f:
    f.write(content)
with open('server.py', 'w', encoding='utf-8') as f:
    f.write(server_content)
print("NaN fixed!")
