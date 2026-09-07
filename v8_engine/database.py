import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "v8_signals.db")

class V8Database:
    @staticmethod
    def get_connection():
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def init_db():
        conn = V8Database.get_connection()
        cursor = conn.cursor()
        
        # Sinyal ana tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS v8_signals (
                signal_id TEXT PRIMARY KEY,
                symbol TEXT,
                timestamp TEXT,
                strategy TEXT,
                market_regime TEXT,
                score REAL,
                entry_price REAL,
                stop_price REAL,
                target1 REAL,
                target2 REAL,
                features_snapshot TEXT,
                status TEXT
            )
        ''')
        
        # Sonuc takip tablosu (Outcome Engine icin)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS v8_outcomes (
                signal_id TEXT PRIMARY KEY,
                t_3m_price REAL,
                t_5m_price REAL,
                t_10m_price REAL,
                t_15m_price REAL,
                t_30m_price REAL,
                t_60m_price REAL,
                t_120m_price REAL,
                t_240m_price REAL,
                t_eod_price REAL,
                t_1d_price REAL,
                max_favorable_excursion REAL,
                max_adverse_excursion REAL,
                final_result TEXT
            )
        ''')
        
        # Piyasa Rejimi Gecmisi (Analiz icin)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS v8_market_regimes (
                timestamp TEXT PRIMARY KEY,
                regime TEXT,
                regime_score REAL,
                xu100_trend REAL,
                volatility_state TEXT
            )
        ''')
        
        conn.commit()
        V8Database._migrate_outcomes(cursor, conn)
        conn.close()
        
    @staticmethod
    def _migrate_outcomes(cursor, conn):
        """Mevcut v8_outcomes tablosuna eksik kolonlari ekler."""
        cursor.execute("PRAGMA table_info(v8_outcomes)")
        existing = {row['name'] for row in cursor.fetchall()}
        needed = {
            't_3m_price': 'REAL',
            't_10m_price': 'REAL',
            't_120m_price': 'REAL',
            't_240m_price': 'REAL',
            't_1d_price': 'REAL',
        }
        for col, ctype in needed.items():
            if col not in existing:
                try:
                    cursor.execute(f"ALTER TABLE v8_outcomes ADD COLUMN {col} {ctype}")
                    print(f"[V8 DB Migration] Added column {col}")
                except Exception as e:
                    print(f"[V8 DB Migration] {col} error: {e}")
        conn.commit()
        
    @staticmethod
    def save_signal(signal_data: dict):
        try:
            conn = V8Database.get_connection()
            cursor = conn.cursor()
            
            features = signal_data.get('features_snapshot', {})
            features_str = json.dumps(features) if isinstance(features, dict) else features
            
            cursor.execute('''
                INSERT OR REPLACE INTO v8_signals 
                (signal_id, symbol, timestamp, strategy, market_regime, score, entry_price, stop_price, target1, target2, features_snapshot, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_data.get('signal_id'),
                signal_data.get('symbol'),
                signal_data.get('timestamp', datetime.now().isoformat()),
                signal_data.get('strategy', 'UNKNOWN'),
                signal_data.get('market_regime', 'NEUTRAL'),
                signal_data.get('score', 0.0),
                signal_data.get('entry_price', 0.0),
                signal_data.get('stop_price', 0.0),
                signal_data.get('target1', 0.0),
                signal_data.get('target2', 0.0),
                features_str,
                signal_data.get('status', 'ACTIVE')
            ))
            conn.commit()
        except Exception as e:
            print(f"[V8 DB Error] Save Signal: {e}")
        finally:
            if 'conn' in locals(): conn.close()
