"""
SQLite uyumlu ince DB adaptoru.
- DATABASE_URL (veya SUPABASE_DB_URL) tanimliysa PostgreSQL (Supabase) kullanir.
- Tanimli degilse klasik yerel SQLite ile calisir (yerel gelistirme bozulmaz).

Kod tabanindaki mevcut SQL'ler (soru isareti placeholder, sqlite3.Row benzeri erisim,
INSERT OR IGNORE / INSERT OR REPLACE, PRAGMA table_info, AUTOINCREMENT) Postgres'e
otomatik cevrilir; cagiran kodlar degismeden calisir.
"""
import os
import re
import threading

DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("SUPABASE_DB_URL")
    or ""
).strip()
IS_PG = bool(DATABASE_URL)

if IS_PG:
    import psycopg2

# ---------------------------------------------------------------- yardimcilar

_PK_CACHE = {}
_pk_lock = threading.Lock()


def _pg_table_pks(cur, table):
    """Tablonun primary key kolonlarini information_schema/pg_index'ten ceker."""
    with _pk_lock:
        if table in _PK_CACHE:
            return _PK_CACHE[table]
    try:
        cur.execute(
            "SELECT a.attname FROM pg_index i "
            "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
            "WHERE i.indrelid = %s::regclass AND i.indisprimary",
            (table,),
        )
        pks = sorted({r[0] for r in cur.fetchall()})
    except Exception:
        pks = []
    with _pk_lock:
        _PK_CACHE[table] = pks
    return pks


def _translate_sql(sql: str, cur) -> str:
    s = sql.strip()

    # PRAGMA table_info(t) -> information_schema karşiliği (row[1] ve row['name'] calisir)
    m = re.match(r"PRAGMA\s+table_info\(\s*(\w+)\s*\)", s, re.I)
    if m:
        t = m.group(1)
        return (
            "SELECT ordinal_position AS cid, column_name AS name, data_type AS type, "
            "0 AS notnull, NULL AS dflt_value, 0 AS pk "
            f"FROM information_schema.columns WHERE table_name = '{t}' "
            "ORDER BY ordinal_position"
        )

    # AUTOINCREMENT -> BIGSERIAL
    s = re.sub(
        r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT",
        "BIGSERIAL PRIMARY KEY",
        s,
        flags=re.I,
    )

    # INSERT OR IGNORE -> ON CONFLICT DO NOTHING
    if re.search(r"INSERT\s+OR\s+IGNORE\s+INTO", s, re.I):
        s = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", s, flags=re.I)
        if not re.search(r"ON\s+CONFLICT", s, re.I):
            s += " ON CONFLICT DO NOTHING"
        return _ph(s)

    # INSERT OR REPLACE -> PK uzerinden upsert
    m = re.search(
        r"INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\(([^)]*)\)\s*VALUES", s, re.I
    )
    if m:
        table = m.group(1)
        cols = [c.strip().strip('"') for c in m.group(2).split(",")]
        pks = _pg_table_pks(cur, table)
        s = re.sub(r"INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", s, flags=re.I)
        upd = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c not in pks)
        if pks and upd:
            s += f" ON CONFLICT ({', '.join(pks)}) DO UPDATE SET {upd}"
        else:
            s += " ON CONFLICT DO NOTHING"
        return _ph(s)

    return _ph(s)


def _ph(s: str) -> str:
    """SQLite '?' placeholder'larini psycopg2 '%s'e cevirir."""
    return s.replace("?", "%s")


class RowLike(tuple):
    """sqlite3.Row benzeri: hem indeks hem kolon adi ile erisim."""
    _desc = ()

    def __getitem__(self, key):
        if isinstance(key, str):
            try:
                return tuple.__getitem__(self, self._desc.index(key))
            except ValueError:
                raise IndexError(f"Column not found: {key}")
        return tuple.__getitem__(self, key)

    def keys(self):
        return list(self._desc)

    def get(self, key, default=None):
        try:
            return self[key]
        except (IndexError, KeyError):
            return default


class PGCursor:
    def __init__(self, raw_cursor):
        self._cur = raw_cursor
        self._names = None

    def execute(self, sql, params=()):
        sql2 = _translate_sql(sql, self._cur)
        self._cur.execute(sql2, tuple(params) if params else None)
        if self._cur.description:
            self._names = [d[0] for d in self._cur.description]
        else:
            self._names = None

    def _wrap(self, row):
        if row is None:
            return None
        r = RowLike(row)
        r._desc = self._names or []
        return r

    def fetchone(self):
        return self._wrap(self._cur.fetchone())

    def fetchall(self):
        rows = self._cur.fetchall() or []
        return [self._wrap(r) for r in rows]

    @property
    def rowcount(self):
        return self._cur.rowcount

    def close(self):
        self._cur.close()


class PGConn:
    def __init__(self, dsn):
        self._conn = psycopg2.connect(
            dsn,
            connect_timeout=15,
            sslmode="require",
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=3,
        )

    def cursor(self):
        return PGCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    row_factory = None  # kod 'conn.row_factory = sqlite3.Row' atiyorsa zarar vermez

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            try:
                self.rollback()
            except Exception:
                pass
        else:
            try:
                self.commit()
            except Exception:
                raise
        return False


def connect():
    """Adaptörün doğrudan bağlantı fabrikası (migration scriptleri için)."""
    if not IS_PG:
        raise RuntimeError("pg_store: DATABASE_URL tanimli degil, PostgreSQL modu kapali")
    return PGConn(DATABASE_URL)
