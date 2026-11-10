with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update allowed list
old_allowed = "allowed = ['/login', '/logout', '/api/ping', '/api/auth_config', '/api/auth/session', '/api/system/git_pull', '/api/system/deploy', '/api/system/sync_verdent', '/api/system/push_market_data', '/api/system/network_test', '/api/system/fast_scan']"
new_allowed = "allowed = ['/login', '/logout', '/api/ping', '/api/auth_config', '/api/auth/session', '/api/system/git_pull', '/api/system/deploy', '/api/system/sync_verdent', '/api/system/push_market_data', '/api/cron/sync_to_pa', '/api/system/network_test', '/api/system/fast_scan']"

if old_allowed in text:
    text = text.replace(old_allowed, new_allowed, 1)
    print("Allowed list updated")
else:
    print("WARNING: old_allowed not found")

# 2. Add route before push_market_data
target = "@app.route('/api/system/push_market_data', methods=['POST'])"
cron_route = """@app.route('/api/cron/sync_to_pa', methods=['GET', 'POST'])
def api_cron_sync_to_pa():
    \"\"\"Harici cron servisi (cron-job.org vb. 8 dakikada bir) bu adresi vurdugunda,
    Verdent en taze BIST verilerini PythonAnywhere'e enjekte eder ve simulasyonu tetikler.\"\"\"
    try:
        global GLOBAL_DASHBOARD_CACHE
        dash_data = GLOBAL_DASHBOARD_CACHE if (isinstance(GLOBAL_DASHBOARD_CACHE, dict) and GLOBAL_DASHBOARD_CACHE.get('all_symbols_stats')) else None
        if not dash_data:
            try:
                with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
                    dash_data = json.load(f)
            except Exception:
                pass

        v8_bo = None
        try:
            with open('v8_breakout_cache.json', 'r', encoding='utf-8') as f:
                v8_bo = json.load(f)
        except Exception:
            pass

        if not dash_data or not dash_data.get('all_symbols_stats'):
            return jsonify({"status": "warning", "message": "Henuz taze veri yok, cache bos."}), 200

        payload = {
            "token": "pro8_sync",
            "dashboard_data": dash_data,
            "v8_breakout_data": v8_bo
        }

        import requests
        r = requests.post(
            "https://varantradarpro.pythonanywhere.com/api/system/push_market_data?token=pro8_sync",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=35
        )
        return jsonify({
            "status": "success",
            "message": "Verdent verileri PythonAnywhere'e basariyla aktarildi (8 dk dongusu).",
            "pa_status": r.status_code,
            "pa_response": r.json() if r.status_code == 200 else r.text[:200]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/system/push_market_data', methods=['POST'])"""

if target in text:
    text = text.replace(target, cron_route, 1)
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: cron route added to server.py")
else:
    print("ERROR: target not found")
