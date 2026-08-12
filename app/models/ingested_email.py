"""Modelo CorreoIngerido (data-model.md § CorreoIngerido) — deduplicación FR-009 (feature 001) y
`estado_procesamiento`/`motivo_fallo` de specs/006-lotes-aprobacion-previa/ (FR-009 a FR-011)."""

from dataclasses import dataclass

from app.db.session import get_connection


@dataclass(frozen=True)
class IngestedEmail:
    id: int
    cuenta_id: int
    proveedor_message_id: str
    remitente: str
    asunto: str
    fecha_correo: str
    primera_sincronizacion_id: int
    estado_procesamiento: str
    motivo_fallo: str | None

    @classmethod
    def _from_row(cls, row) -> "IngestedEmail":
        return cls(
            id=row["id"],
            cuenta_id=row["cuenta_id"],
            proveedor_message_id=row["proveedor_message_id"],
            remitente=row["remitente"],
            asunto=row["asunto"],
            fecha_correo=row["fecha_correo"],
            primera_sincronizacion_id=row["primera_sincronizacion_id"],
            estado_procesamiento=row["estado_procesamiento"],
            motivo_fallo=row["motivo_fallo"],
        )


def find_existing(cuenta_id: int, proveedor_message_id: str) -> IngestedEmail | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM ingested_emails WHERE cuenta_id = ? AND proveedor_message_id = ?",
        (cuenta_id, proveedor_message_id),
    ).fetchone()
    return IngestedEmail._from_row(row) if row else None


def create(
    cuenta_id: int,
    proveedor_message_id: str,
    remitente: str,
    asunto: str,
    fecha_correo: str,
    primera_sincronizacion_id: int,
    estado_procesamiento: str = "PENDIENTE",
) -> IngestedEmail:
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO ingested_emails
            (cuenta_id, proveedor_message_id, remitente, asunto, fecha_correo,
             primera_sincronizacion_id, estado_procesamiento)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cuenta_id,
            proveedor_message_id,
            remitente,
            asunto,
            fecha_correo,
            primera_sincronizacion_id,
            estado_procesamiento,
        ),
    )
    conn.commit()
    return get_by_id(cursor.lastrowid)


def get_by_id(correo_id: int) -> IngestedEmail | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM ingested_emails WHERE id = ?", (correo_id,)).fetchone()
    return IngestedEmail._from_row(row) if row else None


def list_pendientes_o_fallidos(sync_run_id: int) -> list[IngestedEmail]:
    """FR-007/FR-009: correos de este lote que todavía necesitan procesarse (primera vez) o
    reintentarse (tras un fallo)."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM ingested_emails
        WHERE primera_sincronizacion_id = ? AND estado_procesamiento IN ('PENDIENTE', 'FALLIDO')
        """,
        (sync_run_id,),
    ).fetchall()
    return [IngestedEmail._from_row(row) for row in rows]


def list_fallidos(sync_run_id: int) -> list[IngestedEmail]:
    """FR-010: correos fallidos de este lote, visibles para la persona autorizada."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM ingested_emails
        WHERE primera_sincronizacion_id = ? AND estado_procesamiento = 'FALLIDO'
        """,
        (sync_run_id,),
    ).fetchall()
    return [IngestedEmail._from_row(row) for row in rows]


def marcar_procesado(correo_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE ingested_emails SET estado_procesamiento = 'PROCESADO', motivo_fallo = NULL "
        "WHERE id = ?",
        (correo_id,),
    )
    conn.commit()


def marcar_fallido(correo_id: int, motivo: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE ingested_emails SET estado_procesamiento = 'FALLIDO', motivo_fallo = ? "
        "WHERE id = ?",
        (motivo, correo_id),
    )
    conn.commit()
