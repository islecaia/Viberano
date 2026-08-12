"""Modelo Extracto Bancario (data-model.md § BankStatement)."""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.session import get_connection


@dataclass(frozen=True)
class BankStatement:
    id: int
    fecha_inicio: str
    fecha_fin: str
    aportado_por: str
    fecha_aporte: str
    total_movimientos: int

    @classmethod
    def _from_row(cls, row) -> "BankStatement":
        return cls(
            id=row["id"],
            fecha_inicio=row["fecha_inicio"],
            fecha_fin=row["fecha_fin"],
            aportado_por=row["aportado_por"],
            fecha_aporte=row["fecha_aporte"],
            total_movimientos=row["total_movimientos"],
        )


def create(
    fecha_inicio: str, fecha_fin: str, aportado_por: str, total_movimientos: int
) -> BankStatement:
    conn = get_connection()
    fecha_aporte = datetime.now(UTC).isoformat()
    cursor = conn.execute(
        """
        INSERT INTO bank_statements
            (fecha_inicio, fecha_fin, aportado_por, fecha_aporte, total_movimientos)
        VALUES (?, ?, ?, ?, ?)
        """,
        (fecha_inicio, fecha_fin, aportado_por, fecha_aporte, total_movimientos),
    )
    conn.commit()
    return get_by_id(cursor.lastrowid)


def get_by_id(statement_id: int) -> BankStatement | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM bank_statements WHERE id = ?", (statement_id,)).fetchone()
    return BankStatement._from_row(row) if row else None
