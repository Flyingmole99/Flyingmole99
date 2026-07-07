"""DB-Verbindungspool + FastAPI-Dependency (eine Transaktion je Request)."""
from __future__ import annotations

import os

from psycopg2.pool import ThreadedConnectionPool

_pool: ThreadedConnectionPool | None = None


def init_pool(dsn: str | None = None, minconn: int = 1, maxconn: int = 8) -> None:
    global _pool
    dsn = dsn or os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL nicht gesetzt")
    _pool = ThreadedConnectionPool(minconn, maxconn, dsn)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


def get_cursor():
    """Yield-Dependency: Cursor in einer Transaktion; commit bei Erfolg, sonst rollback."""
    if _pool is None:
        init_pool()
    conn = _pool.getconn()
    conn.set_client_encoding("UTF8")
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        _pool.putconn(conn)
