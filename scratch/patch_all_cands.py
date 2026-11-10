with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''    cands = dash_data.get('tavan_adaylari', []) or []
    from services.market_data import MarketDataManager
    if cands:
        MarketDataManager.record_signals(date_str, cands)'''

replacement = '''    all_cands = list(dash_data.get('tavan_adaylari', []) or [])
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
            pass'''

if target in text:
    new_text = text.replace(target, replacement, 1)
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("SUCCESS: server.py updated with all_cands")
else:
    print("FAILED: target not found")
