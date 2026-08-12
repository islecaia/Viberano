"""Candidatos de conciliación ambiguos (data-model.md § ReconciliationCandidate).

Solo existen mientras un documento está `PENDIENTE REVISIÓN CONCILIACIÓN` (FR-005); al resolverse
(FR-006) se eliminan con `clear_for_documento`.
"""

from dataclasses import dataclass

from app.db.session import get_connection


@dataclass(frozen=True)
class ReconciliationCandidate:
    id: int
    documento_id: int
    movimiento_id: int

    @classmethod
    def _from_row(cls, row) -> "ReconciliationCandidate":
        return cls(
            id=row["id"], documento_id=row["documento_id"], movimiento_id=row["movimiento_id"]
        )


def create_many(documento_id: int, movimiento_ids: list[int]) -> None:
    conn = get_connection()
    conn.executemany(
        "INSERT INTO reconciliation_candidates (documento_id, movimiento_id) VALUES (?, ?)",
        [(documento_id, movimiento_id) for movimiento_id in movimiento_ids],
    )
    conn.commit()


def list_for_documento(documento_id: int) -> list[ReconciliationCandidate]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM reconciliation_candidates WHERE documento_id = ?", (documento_id,)
    ).fetchall()
    return [ReconciliationCandidate._from_row(row) for row in rows]


def clear_for_documento(documento_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM reconciliation_candidates WHERE documento_id = ?", (documento_id,))
    conn.commit()
