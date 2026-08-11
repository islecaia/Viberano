"""Conexión SQLite en modo WAL (research.md §7 de la feature 001): una única conexión de
escritura por proceso, más un runner de migraciones versionadas (research.md §1-§2 de
specs/002-validacion-archivado-facturas/)."""

import logging
import os
import sqlite3
import threading
from pathlib import Path

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"

_local = threading.local()
logger = logging.getLogger("invoice_manager")


def _db_path() -> str:
    return os.environ.get("SQLITE_DB_PATH", "./data/invoice_manager.db")


def init_db() -> None:
    """Crea el directorio de datos y aplica las migraciones pendientes (idempotente)."""
    path = Path(_db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    _apply_pending_migrations()


def _apply_pending_migrations() -> None:
    conn = get_connection()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT)"
    )
    conn.commit()

    applied = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}
    pending = sorted(
        p for p in _MIGRATIONS_DIR.glob("*.sql") if p.stem not in applied
    )
    for migration_path in pending:
        version = migration_path.stem
        try:
            conn.executescript(migration_path.read_text(encoding="utf-8"))
        except sqlite3.Error:
            conn.rollback()
            logger.exception("Fallo aplicando la migración %s; revertida", version)
            raise
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, datetime('now'))",
            (version,),
        )
        conn.commit()
        logger.info("Migración aplicada: %s", version)


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
