import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any

DB_PATH = os.path.join("data", "trading_engine.db")

def get_connection():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Signals Table (Sabah üretilen adaylar)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_str TEXT NOT NULL,
            symbol TEXT NOT NULL,
            score REAL,
            morning_price REAL,
            ceiling_target REAL,
            morning_phase TEXT,
            metadata TEXT,
            UNIQUE(date_str, symbol)
        )
    """)
    
    # 2. MarketData Table (Sinyal üretilen hisselerin 5 dakikalık OHLC logu)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_str TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            UNIQUE(timestamp, symbol)
        )
    """)
    
    # 3. Trades Table (Simülasyon sonuçları)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_str TEXT NOT NULL,
            symbol TEXT NOT NULL,
            entry_time TEXT NOT NULL,
            entry_price REAL NOT NULL,
            exit_time TEXT,
            exit_price REAL,
            shares INTEGER,
            pnl_val REAL,
            pnl_pct REAL,
            exit_reason TEXT,
            UNIQUE(date_str, symbol, entry_time)
        )
    """)
    
    # 4. Simulation Equity Log (Günlük bakiye değişimi)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equity_log (
            date_str TEXT PRIMARY KEY,
            start_equity REAL,
            end_equity REAL,
            daily_pnl REAL,
            total_trades INTEGER,
            win_trades INTEGER
        )
    """)

    # 5. Live Positions (Anlık işlem terminali - manuel + akıllı TP/SL motoru)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS live_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_str TEXT NOT NULL,
            symbol TEXT NOT NULL,
            entry_time TEXT NOT NULL,
            entry_price REAL NOT NULL,
            shares INTEGER NOT NULL,
            cost_val REAL,
            stop_price REAL,
            tp_price REAL,
            trail_pct REAL DEFAULT 0,
            high_water REAL,
            trailing_active INTEGER DEFAULT 0,
            status TEXT DEFAULT 'OPEN',
            source TEXT DEFAULT 'MANUAL',
            exit_time TEXT,
            exit_price REAL,
            pnl_val REAL,
            pnl_pct REAL,
            exit_reason TEXT,
            last_price REAL,
            last_update TEXT
        )
    """)

    # 6. Live Settings (Canlı hesap bakiyesi vb.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS live_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO live_settings (key, value) VALUES ('live_cash', '100000.0')
    """)
    # Tek seferlik migrasyon: mevcut bakiyeyi 100.000 TL'ye yukselt (her deploy'da sifirlanmasin)
    cursor.execute("SELECT value FROM live_settings WHERE key='live_cash_migrated_100k'")
    if cursor.fetchone() is None:
        cursor.execute("UPDATE live_settings SET value='100000.0' WHERE key='live_cash'")
        cursor.execute("INSERT OR IGNORE INTO live_settings (key, value) VALUES ('live_cash_migrated_100k', '1')")

    conn.commit()
    conn.close()

# Start initialization
init_db()
