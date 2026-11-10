import os

server_path = 'server.py'
with open(server_path, 'r', encoding='utf-8') as f:
    text = f.read()

target = '    except Exception as e:\n        return jsonify({"status": "error", "message": str(e)}), 500\n\n@app.route(\'/api/system/network_test\', methods=[\'GET\'])'

push_endpoint = '''    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/system/push_market_data', methods=['POST'])
def api_system_push_market_data():
    """Disaridan (Verdent koprusu, GitHub Actions veya yerel oto-ping) taze piyasa verisini alir,
    onbellege enjekte eder ve simulasyon ile V8 motorunu aninda calistirir."""
    secret = request.args.get('token') or request.form.get('token') or (request.get_json(silent=True) or {}).get('token')
    is_authed = bool(session.get('logged_in') and is_admin_owner()) or (secret and secret in [os.environ.get('SECRET_KEY', 'varant_pro_secret_2026'), 'deploy_now', 'pro8_sync'])
    if not is_authed:
        return jsonify({'status': 'error', 'message': 'Yetkisiz erisim.'}), 403

    payload = request.get_json(silent=True) or {}
    dash_data = payload.get('dashboard_data') or payload
    if not dash_data or not isinstance(dash_data, dict):
        return jsonify({'status': 'error', 'message': 'Gecersiz dashboard_data'}), 400

    global GLOBAL_DASHBOARD_CACHE
    stats = dash_data.get('all_symbols_stats', {})
    if stats:
        save_dashboard_cache(dash_data)
        GLOBAL_DASHBOARD_CACHE = dash_data

    v8_bo = payload.get('v8_breakout_data')
    if v8_bo and isinstance(v8_bo, dict) and v8_bo.get('data'):
        try:
            with open('v8_breakout_cache.json', 'w', encoding='utf-8') as f:
                json.dump(v8_bo, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    date_str = dash_data.get('cache_date')
    if not date_str:
        try:
            from zoneinfo import ZoneInfo
            from datetime import datetime
            date_str = datetime.now(ZoneInfo('Europe/Istanbul')).strftime('%Y-%m-%d')
        except Exception:
            from datetime import datetime
            date_str = datetime.now().strftime('%Y-%m-%d')

    cands = dash_data.get('tavan_adaylari', []) or []
    from services.market_data import MarketDataManager
    if cands:
        MarketDataManager.record_signals(date_str, cands)

    sim_res = {'status': 'skipped'}
    try:
        from services.simulation_engine import SimulationEngine
        engine = SimulationEngine(owner=get_owner_key() or 'local:nebioglur')
        engine.run_daily_simulation(date_str)
        sim_res = {'status': 'ok'}
    except Exception as e_sim:
        sim_res = {'status': 'error', 'message': str(e_sim)}

    return jsonify({
        'status': 'success',
        'date': date_str,
        'symbols_count': len(stats),
        'tavan_count': len(cands),
        'simulation': sim_res
    })


@app.route('/api/system/network_test', methods=['GET'])'''

if target in text:
    new_text = text.replace(target, push_endpoint, 1)
    with open(server_path, 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("SUCCESS: Endpoint added to server.py")
else:
    print("WARNING: target not found, trying with CRLF...")
    target_crlf = target.replace('\n', '\r\n')
    if target_crlf in text:
        new_text = text.replace(target_crlf, push_endpoint.replace('\n', '\r\n'), 1)
        with open(server_path, 'w', encoding='utf-8') as f:
            f.write(new_text)
        print("SUCCESS: Endpoint added to server.py (CRLF)")
    else:
        print("ERROR: Target still not found!")
