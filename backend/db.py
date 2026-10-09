import threading

import psycopg2
import psycopg2.extras
import psycopg2.pool

from .config import DATABASE_URL

# Reused connections: opening a fresh one per request is slow, and the draft room polls a lot.
# get_db() hands out a pooled connection; its close() rolls back anything uncommitted and returns it.
# If the pool is full (or can't be made), it falls back to a plain new connection.
_KW = dict(cursor_factory=psycopg2.extras.RealDictCursor, keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3)
_pool = None
_lock = threading.Lock()


def _get_pool():
    global _pool
    if _pool is None:
        with _lock:
            if _pool is None:
                _pool = psycopg2.pool.ThreadedConnectionPool(1, 20, DATABASE_URL, **_KW)
    return _pool


class _Pooled:
    """A pooled connection that behaves like a normal one; close() gives it back to the pool."""

    def __init__(self, pool, conn):
        self._pool, self._conn = pool, conn

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        conn, self._conn = self._conn, None
        if conn is None:
            return
        broken = bool(conn.closed)
        if not broken:
            try:
                conn.rollback()  # never hand on a half-finished transaction
            except psycopg2.Error:
                broken = True
        try:
            self._pool.putconn(conn, close=broken)
        except psycopg2.Error:
            pass

    def __del__(self):
        if getattr(self, "_conn", None) is not None:
            try:
                self.close()
            except Exception:
                pass


def get_db():
    try:
        pool = _get_pool()
        conn = pool.getconn()
    except (psycopg2.pool.PoolError, psycopg2.OperationalError):
        return psycopg2.connect(DATABASE_URL, **_KW)
    if conn.closed:  # dropped while idle: replace it
        pool.putconn(conn, close=True)
        conn = pool.getconn()
    return _Pooled(pool, conn)
