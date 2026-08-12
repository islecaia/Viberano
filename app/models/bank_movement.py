"""Modelo Movimiento Bancario (data-model.md § BankMovement).

Un movimiento es una copia fiel de una fila del CSV aportado (Principio I): ningún campo se
modifica tras su creación.
"""

from dataclasses import dataclass

from app.db.session import get_connection


@dataclass(frozen=True)
class BankMovement:
    id: int
    extracto_id: int
    fecha: str
    importe: float
    concepto: str

    @classmethod
    def _from_row(cls, row) -> "BankMovement":
        return cls(
            id=row["id"],
            extracto_id=row["extracto_id"],
            fecha=row["fecha"],
            importe=row["importe"],
            concepto=row["concepto"],
        )


def create_bulk(extracto_id: int, movimientos: list[dict]) -> list[BankMovement]:
    """`movimientos`: lista de {"fecha": str, "importe": float, "concepto": str}."""
    conn = get_connection()
    creados = []
    for mov in movimientos:
        cursor = conn.execute(
            "INSERT INTO bank_movements (extracto_id, fecha, importe, concepto) "
            "VALUES (?, ?, ?, ?)",
            (extracto_id, mov["fecha"], mov["importe"], mov["concepto"]),
        )
        creados.append(cursor.lastrowid)
    conn.commit()
    return [get_by_id(mid) for mid in creados]


def get_by_id(movement_id: int) -> BankMovement | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM bank_movements WHERE id = ?", (movement_id,)).fetchone()
    return BankMovement._from_row(row) if row else None


def find_candidatos(
    extracto_id: int, importe_objetivo: float, fecha_factura: str, ventana_dias: int = 10
) -> list[BankMovement]:
    """FR-002/research.md §3: movimientos del extracto con el mismo importe absoluto, dentro de
    una ventana de fechas alrededor de `fecha_factura`, y que no estén ya vinculados a otra
    factura (FR-009)."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT bm.* FROM bank_movements bm
        WHERE bm.extracto_id = ?
          AND ABS(bm.importe) = ?
          AND bm.fecha BETWEEN date(?, ?) AND date(?, ?)
          AND bm.id NOT IN (
              SELECT movimiento_bancario_id FROM candidate_documents
              WHERE movimiento_bancario_id IS NOT NULL
          )
        ORDER BY bm.fecha
        """,
        (
            extracto_id,
            abs(importe_objetivo),
            fecha_factura,
            f"-{ventana_dias} days",
            fecha_factura,
            f"+{ventana_dias} days",
        ),
    ).fetchall()
    return [BankMovement._from_row(row) for row in rows]


def find_pendientes_de_justificar(extracto_id: int) -> list[BankMovement]:
    """FR-007/FR-008: cargos (`importe < 0`) de este extracto sin ninguna factura vinculada.
    Los ingresos (`importe > 0`) nunca aparecen aquí (research.md §5)."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT bm.* FROM bank_movements bm
        WHERE bm.extracto_id = ?
          AND bm.importe < 0
          AND bm.id NOT IN (
              SELECT movimiento_bancario_id FROM candidate_documents
              WHERE movimiento_bancario_id IS NOT NULL
          )
        ORDER BY bm.fecha
        """,
        (extracto_id,),
    ).fetchall()
    return [BankMovement._from_row(row) for row in rows]
