import os

with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = "@app.route('/api/v8/radar/breakout', methods=['GET'])"
idx = text.find(target)
if idx != -1:
    insert = """
@app.route('/api/v8/learning/outcomes', methods=['GET'])
@login_required
def api_v8_learning_outcomes():
    try:
        from v8_engine.database import V8Database
        conn = V8Database.get_connection()
        cursor = conn.cursor()
        
        # Sinyalleri ve sonuclarini JOIN ile getir
        query = '''
            SELECT s.signal_id, s.symbol, s.timestamp, s.entry_price, s.score, s.status, s.market_regime,
                   o.t_5m_price, o.t_15m_price, o.t_30m_price, o.t_60m_price,
                   o.max_favorable_excursion as mfe, o.max_adverse_excursion as mae, o.final_result
            FROM v8_signals s
            LEFT JOIN v8_outcomes o ON s.signal_id = o.signal_id
            ORDER BY s.timestamp DESC
            LIMIT 50
        '''
        cursor.execute(query)
        rows = cursor.fetchall()
        
        outcomes = []
        for r in rows:
            outcomes.append({
                "signal_id": r["signal_id"],
                "symbol": r["symbol"],
                "timestamp": r["timestamp"],
                "entry_price": r["entry_price"],
                "score": r["score"],
                "status": r["status"],
                "market_regime": r["market_regime"],
                "t_5m_price": r["t_5m_price"],
                "t_15m_price": r["t_15m_price"],
                "t_30m_price": r["t_30m_price"],
                "t_60m_price": r["t_60m_price"],
                "mfe": r["mfe"],
                "mae": r["mae"],
                "final_result": r["final_result"]
            })
            
        conn.close()
        return jsonify({"status": "success", "data": outcomes})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
"""
    if 'api_v8_learning_outcomes' not in text:
        text = text[:idx] + insert + "\n" + text[idx:]
        with open('server.py', 'w', encoding='utf-8') as f:
            f.write(text)
        print('Outcome API endpoint added.')
    else:
        print('Already exists')
else:
    print('Target not found')
