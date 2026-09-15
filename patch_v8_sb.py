# -*- coding: utf-8 -*-
with open('v8_engine/database.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# init_db
old_init = r'''        try:
            os\.makedirs\("data", exist_ok=True\)
            conn = sqlite3\.connect\(cls\.DB_PATH\)
        except Exception as e:
            print\(f"\[V8 DB INIT FALLBACK\] Disk hatasi: \{e\}\. In-memory DB kullanilacak!"\)
            cls\.DB_PATH = ":memory:"
            conn = sqlite3\.connect\(cls\.DB_PATH\)
        
        cursor = conn\.cursor\(\)
        cursor\.execute\("""
            CREATE TABLE IF NOT EXISTS v8_signals \(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                signal_type TEXT,
                state TEXT,
                entry_price REAL,
                target_price REAL,
                stop_price REAL,
                confidence_score INTEGER,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                outcome TEXT,
                outcome_time TIMESTAMP,
                outcome_profit_pct REAL,
                ai_consensus TEXT,
                features TEXT
            \)
        """\)
        conn\.commit\(\)
        conn\.close\(\)'''
new_init = '''        try:
            from services.supabase_client import get_supabase
            sb = get_supabase()
            if not sb:
                raise Exception("Supabase Client is None")
        except Exception as e:
            print(f"[V8 DB INIT] Supabase hazir degil, SQLite (memory) fallback deneniyor. {e}")
            cls.DB_PATH = ":memory:"
            conn = sqlite3.connect(cls.DB_PATH)
            conn.cursor().execute("""CREATE TABLE IF NOT EXISTS v8_signals (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, signal_type TEXT, state TEXT, entry_price REAL, target_price REAL, stop_price REAL, confidence_score INTEGER, detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, outcome TEXT, outcome_time TIMESTAMP, outcome_profit_pct REAL, ai_consensus TEXT, features TEXT)""")
            conn.commit()
            conn.close()'''
content = re.sub(old_init, new_init, content)

# insert_signal
old_insert = r'''        conn = cls\.get_connection\(\)
        cursor = conn\.cursor\(\)
        try:
            features_str = json\.dumps\(features\) if isinstance\(features, dict\) else features
            cursor\.execute\("""
                INSERT INTO v8_signals 
                \(symbol, signal_type, state, entry_price, target_price, stop_price, confidence_score, ai_consensus, features, outcome\)
                VALUES \(\?, \?, \?, \?, \?, \?, \?, \?, \?, 'PENDING'\)
            """, \(symbol, signal_type, state, entry_price, target_price, stop_price, confidence_score, ai_consensus, features_str\)\)
            conn\.commit\(\)
            return True
        except Exception as e:
            print\(f"\[V8 DB Insert Error\] \{e\}"\)
            return False
        finally:
            conn\.close\(\)'''
new_insert = '''        try:
            from services.supabase_client import get_supabase
            sb = get_supabase()
            features_str = json.dumps(features) if isinstance(features, dict) else features
            data = {
                "symbol": symbol, "signal_type": signal_type, "state": state,
                "entry_price": entry_price, "target_price": target_price, "stop_price": stop_price,
                "confidence_score": confidence_score, "ai_consensus": ai_consensus,
                "features": features_str, "outcome": "PENDING"
            }
            if sb:
                sb.table("v8_signals").insert(data).execute()
                return True
            else:
                conn = cls.get_connection()
                conn.cursor().execute("INSERT INTO v8_signals (symbol, signal_type, state, entry_price, target_price, stop_price, confidence_score, ai_consensus, features, outcome) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')", (symbol, signal_type, state, entry_price, target_price, stop_price, confidence_score, ai_consensus, features_str))
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            print(f"[V8 DB Insert Error] {e}")
            return False'''
content = re.sub(old_insert, new_insert, content)

with open('v8_engine/database.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("PATCH_V8_DB_OK")
