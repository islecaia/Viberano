"""Modelo Adjunto Pendiente (data-model.md § AdjuntoPendiente de
specs/006-lotes-aprobacion-previa/).

Un adjunto ya guardado en `attachment_store` (Principio III/IV: copia inmutable) pero todavía
sin clasificar — solo existe mientras su correo esté `PENDIENTE` o `FALLIDO` (research.md §2).
"""

from dataclasses import dataclass

from app.db.session import get_connection


@dataclass(frozen=True)
class PendingAttachment:
    id: int
    correo_id: int
    archivo_adjunto_ref: str
    nombre_archivo_original: str
    formato: str

    @classmethod
    def _from_row(cls, row) -> "PendingAttachment":
        return cls(
            id=row["id"],
            correo_id=row["correo_id"],
            archivo_adjunto_ref=row["archivo_adjunto_ref"],
            nombre_archivo_original=row["nombre_archivo_original"],
            formato=row["formato"],
        )


def create(
    correo_id: int, archivo_adjunto_ref: str, nombre_archivo_original: str, formato: str
) -> PendingAttachment:
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO pending_attachments
            (correo_id, archivo_adjunto_ref, nombre_archivo_original, formato)
        VALUES (?, ?, ?, ?)
        """,
        (correo_id, archivo_adjunto_ref, nombre_archivo_original, formato),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM pending_attachments WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return PendingAttachment._from_row(row)


def list_for_correo(correo_id: int) -> list[PendingAttachment]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM pending_attachments WHERE correo_id = ?", (correo_id,)
    ).fetchall()
    return [PendingAttachment._from_row(row) for row in rows]


def delete(pending_attachment_id: int) -> None:
    """Se borra uno a uno según se convierte en `candidate_documents` (no todos juntos al final
    de un correo): si un correo con varios adjuntos falla a mitad, los ya convertidos no deben
    volver a procesarse ni duplicarse en el reintento (research.md §2)."""
    conn = get_connection()
    conn.execute("DELETE FROM pending_attachments WHERE id = ?", (pending_attachment_id,))
    conn.commit()


def delete_for_correo(correo_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM pending_attachments WHERE correo_id = ?", (correo_id,))
    conn.commit()
