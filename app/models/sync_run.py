"""Modelo Sincronizacion (data-model.md § Sincronizacion)."""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.session import get_connection


@dataclass(frozen=True)
class SyncRun:
    id: int
    cuenta_id: int
    iniciada_por: str
    fecha_inicio: str
    fecha_fin: str | None
    estado: str
    correos_procesados: int
    candidatos_generados: int

    @classmethod
    def _from_row(cls, row) -> "SyncRun":
        return cls(
            id=row["id"],
            cuenta_id=row["cuenta_id"],
            iniciada_por=row["iniciada_por"],
            fecha_inicio=row["fecha_inicio"],
            fecha_fin=row["fecha_fin"],
            estado=row["estado"],
            correos_procesados=row["correos_procesados"],
            candidatos_generados=row["candidatos_generados"],
        )


def get_by_id(sync_id: int) -> SyncRun | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM sync_runs WHERE id = ?", (sync_id,)).fetchone()
    return SyncRun._from_row(row) if row else None


def get_en_curso(cuenta_id: int) -> SyncRun | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM sync_runs WHERE cuenta_id = ? AND estado = 'en_curso'", (cuenta_id,)
    ).fetchone()
    return SyncRun._from_row(row) if row else None


def create(cuenta_id: int, iniciada_por: str) -> SyncRun:
    conn = get_connection()
    fecha_inicio = datetime.now(UTC).isoformat()
    cursor = conn.execute(
        """
        INSERT INTO sync_runs (cuenta_id, iniciada_por, fecha_inicio, estado)
        VALUES (?, ?, ?, 'en_curso')
        """,
        (cuenta_id, iniciada_por, fecha_inicio),
    )
    conn.commit()
    return get_by_id(cursor.lastrowid)


def increment_counters(
    sync_id: int, correos_procesados: int = 0, candidatos_generados: int = 0
) -> None:
    conn = get_connection()
    conn.execute(
        """
        UPDATE sync_runs
        SET correos_procesados = correos_procesados + ?,
            candidatos_generados = candidatos_generados + ?
        WHERE id = ?
        """,
        (correos_procesados, candidatos_generados, sync_id),
    )
    conn.commit()


def finish(sync_id: int, estado: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE sync_runs SET estado = ?, fecha_fin = ? WHERE id = ?",
        (estado, datetime.now(UTC).isoformat(), sync_id),
    )
    conn.commit()
