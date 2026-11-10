"""Create the database (if missing) and run schema.sql and seed.sql.

Usage:
    python scripts/init_db.py             # schema + sample data (200 properties)
    python scripts/init_db.py --no-extra  # schema + the small base sample only (used by the tests)
    python scripts/init_db.py --no-seed   # empty schema only
Warning: existing tables are dropped and recreated.
"""
import sys
from pathlib import Path

import psycopg
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402


def main() -> None:
    url = make_url(settings.database_url)
    conninfo = dict(host=url.host or "localhost", port=url.port or 5432, user=url.username, password=url.password)
    conninfo.update(url.query)  # e.g. sslmode=require for hosted Postgres (Neon)

    with psycopg.connect(dbname="postgres", autocommit=True, **conninfo) as conn:
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (url.database,)).fetchone():
            conn.execute(f'CREATE DATABASE "{url.database}" ENCODING \'UTF8\' TEMPLATE template0')
            print(f"database {url.database} created")

    files = ["schema.sql"]
    if "--no-seed" not in sys.argv:
        files.append("seed.sql")
        if "--no-extra" not in sys.argv:
            files.append("seed_extra.sql")
    with psycopg.connect(dbname=url.database, autocommit=True, **conninfo) as conn:
        conn.execute("SET client_min_messages = warning")
        for name in files:
            conn.execute((ROOT / "db" / name).read_text(encoding="utf-8"))
            print(f"{name} applied")
        for table in ("app_user", "property", "unit", "unit_price_calendar", "booking", "payment", "review"):
            count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            print(f"  {table:<22}{count:>6}")


if __name__ == "__main__":
    main()
