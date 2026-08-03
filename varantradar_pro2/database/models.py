import sqlite3
from config.settings import DB_PATH
import os

def create_tables():
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Stock Data Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stock_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        interval TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,
        UNIQUE(symbol, date, interval)
    )
    ''')

    # Indicators Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS technical_indicators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        interval TEXT NOT NULL,
        sma REAL,
        ema REAL,
        rsi REAL,
        macd REAL,
        macd_signal REAL,
        bollinger_upper REAL,
        bollinger_lower REAL,
        vwap REAL,
        atr REAL,
        UNIQUE(stock_symbol, date, interval)
    )
    ''')
    
    # Warrants Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS warrants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        warrant_code TEXT NOT NULL UNIQUE,
        underlying TEXT NOT NULL,
        type TEXT, -- CALL or PUT
        strike_price REAL,
        maturity_date TEXT,
        multiplier REAL
    )
    ''')

    # Favorites & Watchlist Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL UNIQUE,
        is_favorite BOOLEAN DEFAULT 0,
        added_at TEXT NOT NULL
    )
    ''')

    # Analysis History Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS analysis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        interval TEXT NOT NULL,
        score INTEGER,
        action TEXT,
        reasoning TEXT,
        analyzed_at TEXT NOT NULL
    )
    ''')

    # System Logs Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT,
        message TEXT,
        created_at TEXT NOT NULL
    )
    ''')

    # Trade Alerts Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        target_price REAL,
        condition TEXT, -- ABOVE, BELOW
        is_active BOOLEAN DEFAULT 1,
        created_at TEXT NOT NULL
    )
    ''')

    # Statistics Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS statistics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        metric_name TEXT NOT NULL UNIQUE,
        metric_value REAL,
        updated_at TEXT NOT NULL
    )
    ''')

    # Settings Table (V7)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT NOT NULL UNIQUE,
        setting_value TEXT,
        updated_at TEXT NOT NULL
    )
    ''')

    # V11 Enterprise Edition: Çoklu Kullanıcı ve SaaS Altyapısı
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user', -- 'admin', 'user', 'enterprise'
        api_key TEXT UNIQUE,
        created_at TEXT NOT NULL
    )
    ''')

    # AI Decisions & Feedback Table (V8)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ai_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        ai_action TEXT,
        explanation TEXT,
        contrarian_view TEXT,
        confidence_score REAL,
        user_feedback TEXT, -- 'LIKE', 'DISLIKE' or NULL
        created_at TEXT NOT NULL
    )
    ''')

    # V5: PORTFOLIO & POSITION MANAGEMENT TABLES
    
    # 1. Portfolio Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        total_capital REAL DEFAULT 100000.0,
        available_balance REAL DEFAULT 100000.0,
        used_margin REAL DEFAULT 0.0,
        total_pnl REAL DEFAULT 0.0,
        last_updated TEXT NOT NULL
    )
    ''')
    
    # Initialize default portfolio if empty
    cursor.execute("SELECT COUNT(*) FROM portfolio")
    if cursor.fetchone()[0] == 0:
        import datetime
        cursor.execute("INSERT INTO portfolio (total_capital, available_balance, used_margin, total_pnl, last_updated) VALUES (?, ?, ?, ?, ?)",
                       (100000.0, 100000.0, 0.0, 0.0, datetime.datetime.now().isoformat()))

    # 2. Active Positions Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS active_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        asset_type TEXT NOT NULL, -- 'STOCK' or 'WARRANT'
        direction TEXT NOT NULL, -- 'LONG' or 'SHORT'
        quantity INTEGER NOT NULL,
        average_cost REAL NOT NULL,
        current_price REAL,
        unrealized_pnl REAL DEFAULT 0.0,
        stop_loss REAL,
        take_profit REAL,
        opened_at TEXT NOT NULL,
        last_updated TEXT NOT NULL
    )
    ''')

    # 3. Order History Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        order_type TEXT NOT NULL, -- 'MARKET', 'LIMIT', 'STOP'
        action TEXT NOT NULL, -- 'BUY', 'SELL'
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        status TEXT NOT NULL, -- 'FILLED', 'PENDING', 'CANCELLED'
        created_at TEXT NOT NULL,
        executed_at TEXT
    )
    ''')

    # 4. Trade Journal (Completed Trades)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trade_journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        entry_price REAL NOT NULL,
        exit_price REAL NOT NULL,
        realized_pnl REAL NOT NULL,
        pnl_percentage REAL NOT NULL,
        duration_days INTEGER,
        strategy_note TEXT,
        closed_at TEXT NOT NULL
    )
    ''')

    # 5. Scanner Results Table (V13 - Global Dashboard)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scan_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL UNIQUE,
        total_score REAL NOT NULL,
        opportunity_level TEXT,
        eta TEXT,
        stop_eta TEXT,
        risk_reward TEXT,
        trade_quality INTEGER,
        success_prob TEXT,
        trade_type TEXT,
        warrant_code TEXT,
        updated_at TEXT NOT NULL
    )
    ''')

    # 6. Signals History Table (V13 - CFG-01 Radar Başarısı Modülü)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS signals_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        signal_date TEXT NOT NULL,
        trade_type TEXT,
        entry_price REAL,
        target_price REAL,
        stop_loss REAL,
        confidence_score REAL,
        status TEXT DEFAULT 'PENDING', -- PENDING, SUCCESS, FAILED
        exit_price REAL,
        exit_date TEXT
    )
    ''')

    # 7. Watchlist Table (CFG-04 Institutional Trading Workspace)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL UNIQUE,
        added_at TEXT NOT NULL,
        notes TEXT
    )
    ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_tables()
