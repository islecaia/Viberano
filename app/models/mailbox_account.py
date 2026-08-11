"""Modelo CuentaCorreo (data-model.md § CuentaCorreo)."""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.session import get_connection


@dataclass(frozen=True)
class MailboxAccount:
    id: int
    persona_autorizada: str
    proveedor: str
    email_address: str
    estado: str
    credenciales_ref: str
    fecha_conexion: str
    ultima_sincronizacion_cursor: str | None

    @classmethod
    def _from_row(cls, row) -> "MailboxAccount":
        return cls(
            id=row["id"],
            persona_autorizada=row["persona_autorizada"],
            proveedor=row["proveedor"],
            email_address=row["email_address"],
            estado=row["estado"],
            credenciales_ref=row["credenciales_ref"],
            fecha_conexion=row["fecha_conexion"],
            ultima_sincronizacion_cursor=row["ultima_sincronizacion_cursor"],
        )


def get_for_persona(persona_autorizada: str) -> MailboxAccount | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM mailbox_accounts WHERE persona_autorizada = ?", (persona_autorizada,)
    ).fetchone()
    return MailboxAccount._from_row(row) if row else None


def get_by_id(account_id: int) -> MailboxAccount | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM mailbox_accounts WHERE id = ?", (account_id,)).fetchone()
    return MailboxAccount._from_row(row) if row else None


def create(
    persona_autorizada: str, proveedor: str, email_address: str, credenciales_ref: str
) -> MailboxAccount:
    conn = get_connection()
    fecha_conexion = datetime.now(UTC).isoformat()
    cursor = conn.execute(
        """
        INSERT INTO mailbox_accounts
            (persona_autorizada, proveedor, email_address, estado, credenciales_ref, fecha_conexion)
        VALUES (?, ?, ?, 'conectada', ?, ?)
        """,
        (persona_autorizada, proveedor, email_address, credenciales_ref, fecha_conexion),
    )
    conn.commit()
    return get_by_id(cursor.lastrowid)


def update_estado(account_id: int, estado: str) -> None:
    conn = get_connection()
    conn.execute("UPDATE mailbox_accounts SET estado = ? WHERE id = ?", (estado, account_id))
    conn.commit()


def update_cursor(account_id: int, cursor_iso: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE mailbox_accounts SET ultima_sincronizacion_cursor = ? WHERE id = ?",
        (cursor_iso, account_id),
    )
    conn.commit()
