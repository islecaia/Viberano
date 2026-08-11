"""Conexión SQLite en modo WAL (research.md §7): una única conexión de escritura por proceso."""

import os
import sqlite3
import threading
from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

_local = threading.local()


def _db_path() -> str:
    return os.environ.get("SQLITE_DB_PATH", "./data/invoice_manager.db")


def init_db() -> None:
    """Crea el directorio de datos y aplica el esquema (idempotente)."""
    path = Path(_db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def get_connection() -> sqlite3.Connection:
    """Devuelve la conexión del hilo actual, abriéndola en modo WAL si no existe."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(_db_path(), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn
