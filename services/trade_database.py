import sqlite3
import json
import os
from services import pg_store as _pg_store
from datetime import datetime
from typing import List, Dict, Any

from services import pg_store

# DATABASE_URL tanimliysa PostgreSQL (Supabase), degilse yerel SQLite
IS_PG = pg_store.IS_PG
DB_PATH = os.path.join("data", "trading_engine.db")

def get_connection():
    if IS_PG:
        return pg_store.connect()
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _table_columns(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]

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
            interval TEXT NOT NULL DEFAULT '5m',
            source TEXT NOT NULL DEFAULT 'yfinance',
            UNIQUE(timestamp, symbol)
        )
    """)

    # Additive, data-preserving migrations. Never DROP legacy user tables.
    market_columns = _table_columns(cursor, 'market_data')
    if 'interval' not in market_columns:
        cursor.execute("ALTER TABLE market_data ADD COLUMN interval TEXT NOT NULL DEFAULT '5m'")
    if 'source' not in market_columns:
        cursor.execute("ALTER TABLE market_data ADD COLUMN source TEXT NOT NULL DEFAULT 'yfinance'")

    # 3. Trades Table (Simülasyon sonuçları - hesap bazlı)
    # Yeni sart: UNIQUE(owner, date_str, symbol, entry_time).
    # Eski ortak tablo dusurulur (sifirdan baslangic tercihi).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            date_str TEXT NOT NULL,
            symbol TEXT NOT NULL,
            entry_time TEXT NOT NULL,
            entry_price REAL NOT NULL,
            exit_time TEXT,
            exit_price REAL,
            shares INTEGER,
            pnl_val REAL,
            realized_pnl REAL DEFAULT 0,
            pnl_pct REAL,
            exit_reason TEXT,
            strategy_name TEXT,
            entry_score REAL,
            entry_checks TEXT,
            atr_value REAL,
            risk_amount REAL,
            market_regime TEXT,
            UNIQUE(owner, date_str, symbol, entry_time)
        )
    """)
    trade_columns = _table_columns(cursor, 'trades')
    if 'owner' not in trade_columns:
        cursor.execute("ALTER TABLE trades ADD COLUMN owner TEXT")
        trade_columns.append('owner')
    cursor.execute("UPDATE trades SET owner='local:legacy' WHERE owner IS NULL OR owner=''")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_trades_owner_entry ON trades(owner, date_str, symbol, entry_time)")
    for column, definition in [
        ('strategy_name', 'TEXT'),
        ('realized_pnl', 'REAL DEFAULT 0'),
        ('entry_score', 'REAL'),
        ('entry_checks', 'TEXT'),
        ('atr_value', 'REAL'),
        ('risk_amount', 'REAL'),
        ('market_regime', 'TEXT'),
        ('engine_version', "TEXT DEFAULT 'LEGACY'"),
    ]:
        if column not in _table_columns(cursor, 'trades'):
            cursor.execute(f"ALTER TABLE trades ADD COLUMN {column} {definition}")

    # Onceki kapali simulasyon kayitlarinda toplam PnL, gerceklesmis PnL idi.
    cursor.execute("UPDATE trades SET realized_pnl = COALESCE(pnl_val, 0) WHERE exit_time IS NOT NULL AND realized_pnl = 0")

    # 4. Simulation Equity Log (Günlük bakiye değişimi - hesap bazlı)
    # Yeni sart: (owner, date_str) PK. Eski ortak tablo dusurulur (sifirdan baslangic).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equity_log (
            owner TEXT NOT NULL,
            date_str TEXT NOT NULL,
            start_equity REAL,
            end_equity REAL,
            daily_pnl REAL,
            total_trades INTEGER,
            win_trades INTEGER,
            PRIMARY KEY (owner, date_str)
        )
    """)
    equity_columns = _table_columns(cursor, 'equity_log')
    if 'owner' not in equity_columns:
        cursor.execute("ALTER TABLE equity_log ADD COLUMN owner TEXT")
    cursor.execute("UPDATE equity_log SET owner='local:legacy' WHERE owner IS NULL OR owner=''")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_equity_owner_date ON equity_log(owner, date_str)")

    # 5. Live Positions (Anlık işlem terminali - manuel + akıllı TP/SL motoru, hesap bazlı)
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
    if 'owner' not in _table_columns(cursor, 'live_positions'):
        cursor.execute("ALTER TABLE live_positions ADD COLUMN owner TEXT")
    cursor.execute("UPDATE live_positions SET owner='local:legacy' WHERE owner IS NULL OR owner=''")

    # 6. Live Settings (Hesap bazlı bakiye: live_cash:<owner>)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS live_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # 7. App Users (Kayitli hesaplar - owner kaydi)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_users (
            owner_key TEXT PRIMARY KEY,
            email TEXT,
            display_name TEXT,
            created_at TEXT,
            last_login TEXT
        )
    """)

    # 8. Reset Requests (Portfoy sifirlama talepleri)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reset_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_key TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            created_at TEXT,
            processed_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulation_alerts (
            event_key TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()

# Start initialization
init_db()
