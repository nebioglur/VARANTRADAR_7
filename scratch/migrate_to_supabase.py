"""
Yerel SQLite verilerini Supabase Postgres'e tasiyir.
Kullanim: set DATABASE_URL=... && python scratch/migrate_to_supabase.py
"""
import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("SUPABASE_DB_URL")
    or ""
).strip()
if not DATABASE_URL:
    print("HATA: DATABASE_URL ortam degiskeni tanimli degil")
    sys.exit(1)

os.environ["DATABASE_URL"] = DATABASE_URL

from services import pg_store  # noqa: E402
from services import trade_database  # noqa: E402  (import ile init_db -> PG sema olusur)
from v8_engine import database as v8db  # noqa: E402

v8db.V8Database.init_db()  # v8 tablolari PG'de olusur

SQLITE_FILES = {
    "data/trading_engine.db": [
        "signals", "market_data", "live_settings", "live_positions",
        "trades", "equity_log", "app_users", "reset_requests",
    ],
    "data/v8_signals.db": [
        "v8_signals", "v8_outcomes", "v8_market_regimes",
    ],
}

HAS_ID = {"signals", "market_data", "live_positions", "trades", "reset_requests"}


def pg_cols(cur, table):
    cur.execute("PRAGMA table_info(%s)" % table)
    return [r["name"] for r in cur.fetchall()]


def main():
    pg = pg_store.connect()
    pgcur = pg.cursor()
    total = {}

    for db_file, tables in SQLITE_FILES.items():
        if not os.path.exists(db_file):
            print("YOK:", db_file)
            continue
        lite = sqlite3.connect(db_file)
        lite.row_factory = sqlite3.Row
        lite_tables = {r[0] for r in lite.execute("SELECT name FROM sqlite_master WHERE type='table'")}

        for table in tables:
            if table not in lite_tables:
                print("  atla (yerelde yok):", table)
                continue
            cols = pg_cols(pgcur, table)
            if not cols:
                print("  atla (PG'de sema yok):", table)
                continue
            rows = [dict(r) for r in lite.execute("SELECT * FROM %s" % table)]
            if table == "live_settings":
                rows = [r for r in rows if ":" in (r.get("key") or "")]
            n = 0
            for r in rows:
                vals = [r.get(c) for c in cols]
                placeholders = ",".join(["?"] * len(cols))
                collist = ",".join(cols)
                try:
                    pgcur.execute(
                        "INSERT OR IGNORE INTO %s (%s) VALUES (%s)" % (table, collist, placeholders),
                        vals,
                    )
                    n += 1
                except Exception as e:
                    print("   ! %s satir hatasi: %s" % (table, e))
                    try:
                        pg.rollback()
                        pgcur = pg.cursor()
                    except Exception:
                        pass
            # AUTOINCREMENT id'li tablolarda sequence'i gercege cek
            if table in HAS_ID and "id" in cols:
                try:
                    pgcur.execute(
                        "SELECT setval(pg_get_serial_sequence('%s', 'id'), "
                        "COALESCE((SELECT MAX(id) FROM %s), 1))" % (table, table)
                    )
                    pg.commit()
                except Exception as e:
                    print("   ! %s setval hatasi: %s" % (table, e))
                    try:
                        pg.rollback()
                        pgcur = pg.cursor()
                    except Exception:
                        pass
            else:
                pg.commit()
            total[table] = total.get(table, 0) + n
            print("  %s: %d satir gonderildi" % (table, n))
        lite.close()

    pg.commit()
    print("\n--- Ozet ---")
    for t, n in total.items():
        print("%s: %d" % (t, n))
    pg.close()
    print("TASIMA TAMAM")


if __name__ == "__main__":
    main()
