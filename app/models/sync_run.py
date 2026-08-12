"""Modelo Sincronizacion / Lote (data-model.md § Sincronizacion/Lote de
specs/006-lotes-aprobacion-previa/, ampliando specs/001-ingesta-facturas-email/).

`estado` distingue cuatro momentos: `pendiente_aprobacion` (recién analizado, sin clasificar
nada todavía), `en_curso` (ejecutándose), `completada` e `interrumpida`. `completada` no implica
cero fallos (FR-009) — un lote completado puede seguir teniendo correos `FALLIDO` reintentables.
"""

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
    correos_nuevos_detectados: int
    correos_con_adjuntos_candidatos: int

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
            correos_nuevos_detectados=row["correos_nuevos_detectados"],
            correos_con_adjuntos_candidatos=row["correos_con_adjuntos_candidatos"],
        )


def get_by_id(sync_id: int) -> SyncRun | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM sync_runs WHERE id = ?", (sync_id,)).fetchone()
    return SyncRun._from_row(row) if row else None


def get_ultimo(cuenta_id: int) -> SyncRun | None:
    """El lote más reciente de la cuenta, en cualquier estado — para mostrarlo en pantalla
    (pendiente de aprobación, interrumpido, o completado con correos fallidos)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM sync_runs WHERE cuenta_id = ? ORDER BY fecha_inicio DESC LIMIT 1",
        (cuenta_id,),
    ).fetchone()
    return SyncRun._from_row(row) if row else None


def get_pendiente_o_en_curso(cuenta_id: int) -> SyncRun | None:
    """FR-005: como máximo un lote pendiente de aprobación o en ejecución por cuenta a la vez."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM sync_runs WHERE cuenta_id = ? "
        "AND estado IN ('pendiente_aprobacion', 'en_curso')",
        (cuenta_id,),
    ).fetchone()
    return SyncRun._from_row(row) if row else None


def create_analisis(cuenta_id: int, iniciada_por: str) -> SyncRun:
    """FR-001: el lote nace `pendiente_aprobacion` — nada se clasifica todavía."""
    conn = get_connection()
    fecha_inicio = datetime.now(UTC).isoformat()
    cursor = conn.execute(
        """
        INSERT INTO sync_runs (cuenta_id, iniciada_por, fecha_inicio, estado)
        VALUES (?, ?, ?, 'pendiente_aprobacion')
        """,
        (cuenta_id, iniciada_por, fecha_inicio),
    )
    conn.commit()
    return get_by_id(cursor.lastrowid)


def guardar_resumen(
    sync_id: int, correos_nuevos: int, correos_con_adjuntos: int
) -> None:
    """FR-002: resumen mostrado antes de aprobar el lote."""
    conn = get_connection()
    conn.execute(
        """
        UPDATE sync_runs
        SET correos_nuevos_detectados = ?, correos_con_adjuntos_candidatos = ?
        WHERE id = ?
        """,
        (correos_nuevos, correos_con_adjuntos, sync_id),
    )
    conn.commit()


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


def marcar_en_curso(sync_id: int) -> None:
    conn = get_connection()
    conn.execute("UPDATE sync_runs SET estado = 'en_curso' WHERE id = ?", (sync_id,))
    conn.commit()


def marcar_completada(sync_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE sync_runs SET estado = 'completada', fecha_fin = ? WHERE id = ?",
        (datetime.now(UTC).isoformat(), sync_id),
    )
    conn.commit()


def marcar_interrumpida(sync_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE sync_runs SET estado = 'interrumpida', fecha_fin = ? WHERE id = ?",
        (datetime.now(UTC).isoformat(), sync_id),
    )
    conn.commit()
