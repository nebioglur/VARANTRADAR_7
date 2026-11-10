with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''@app.route('/api/system/push_market_data', methods=['POST'])
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

    all_cands = list(dash_data.get('tavan_adaylari', []) or [])
    sim_seen = {c.get('symbol') or c.get('Symbol') for c in all_cands if (c.get('symbol') or c.get('Symbol'))}
    for opp in (dash_data.get('opportunities_1h', []) + dash_data.get('opportunities', [])):
        osym = opp.get('symbol') or opp.get('Symbol')
        if osym and osym not in sim_seen:
            all_cands.append(opp)
            sim_seen.add(osym)
    for sym, st in stats.items():
        if not isinstance(st, dict) or sym in sim_seen: continue
        p = float(st.get('Price') or st.get('Daily_Close') or 0)
        ch = float(st.get('Change_Pct') or 0)
        v = float(st.get('Vol_Multiplier') or st.get('Volume_Ratio') or 0)
        vtl = float(st.get('Volume_TL') or (float(st.get('Volume', 0)) * p) or 0)
        if p >= 4.0 and 0.5 <= ch < 5.2 and v >= 1.2:
            cand = dict(st)
            cand['symbol'] = sym
            cand['score'] = float(st.get('Score') or 92.0)
            cand['morning_price'] = p
            all_cands.append(cand)
            sim_seen.add(sym)

    from services.market_data import MarketDataManager
    if all_cands:
        MarketDataManager.record_signals(date_str, all_cands)
        try:
            MarketDataManager.fetch_and_store_intraday(date_str, period="5d")
        except Exception:
            pass

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
    })'''

replacement = '''@app.route('/api/system/push_market_data', methods=['POST'])
def api_system_push_market_data():
    """Disaridan (Verdent koprusu, GitHub Actions veya yerel oto-ping) taze piyasa verisini alir,
    onbellege enjekte eder ve simulasyon ile V8 motorunu aninda calistirir."""
    try:
        import traceback
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

        all_cands = list(dash_data.get('tavan_adaylari', []) or [])
        sim_seen = {c.get('symbol') or c.get('Symbol') for c in all_cands if (c.get('symbol') or c.get('Symbol'))}
        for opp in (dash_data.get('opportunities_1h', []) + dash_data.get('opportunities', [])):
            osym = opp.get('symbol') or opp.get('Symbol')
            if osym and osym not in sim_seen:
                all_cands.append(opp)
                sim_seen.add(osym)
        for sym, st in stats.items():
            if not isinstance(st, dict) or sym in sim_seen: continue
            try:
                p = float(st.get('Price') or st.get('Daily_Close') or 0)
                ch = float(st.get('Change_Pct') or 0)
                v = float(st.get('Vol_Multiplier') or st.get('Volume_Ratio') or 0)
                if p >= 4.0 and 0.5 <= ch < 5.2 and v >= 1.2:
                    cand = dict(st)
                    cand['symbol'] = sym
                    cand['score'] = float(st.get('Score') or 92.0)
                    cand['morning_price'] = p
                    all_cands.append(cand)
                    sim_seen.add(sym)
            except Exception:
                continue

        from services.market_data import MarketDataManager
        if all_cands:
            MarketDataManager.record_signals(date_str, all_cands)
            try:
                MarketDataManager.fetch_and_store_intraday(date_str, period="5d")
            except Exception:
                pass

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
            'candidates_count': len(all_cands),
            'simulation': sim_res
        })
    except Exception as exc:
        import traceback
        return jsonify({'status': 'error', 'message': str(exc), 'trace': traceback.format_exc()}), 500'''

if target in text:
    new_text = text.replace(target, replacement, 1)
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("SUCCESS: wrapped in try/except")
else:
    print("FAILED: target not found")
