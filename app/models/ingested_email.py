"""Modelo CorreoIngerido (data-model.md § CorreoIngerido) — deduplicación FR-009."""

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
) -> IngestedEmail:
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO ingested_emails
            (cuenta_id, proveedor_message_id, remitente, asunto, fecha_correo,
             primera_sincronizacion_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            cuenta_id,
            proveedor_message_id,
            remitente,
            asunto,
            fecha_correo,
            primera_sincronizacion_id,
        ),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM ingested_emails WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return IngestedEmail._from_row(row)
