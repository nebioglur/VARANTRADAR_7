"""Optional PostgreSQL connectivity smoke check; credentials come from the environment."""
import os


def main():
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        print("SKIP: DATABASE_URL is not configured")
        return 0
    import psycopg2
    with psycopg2.connect(dsn, connect_timeout=10, sslmode="require") as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1
    print("PostgreSQL connectivity check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
