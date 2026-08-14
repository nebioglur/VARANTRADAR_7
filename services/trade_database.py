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
    
    conn.commit()
    conn.close()

# Start initialization
init_db()
