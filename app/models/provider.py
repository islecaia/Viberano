"""Modelo Proveedor (data-model.md § Proveedor, research.md §5).

`nombre` se compara de forma normalizada (minúsculas, sin espacios extra) contra el índice único
`ux_providers_nombre_normalizado` — sin fuzzy matching, solo coincidencia exacta normalizada.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.session import get_connection


@dataclass(frozen=True)
class Provider:
    id: int
    nombre: str
    identificador_fiscal: str | None
    activo: bool
    fecha_alta: str

    @classmethod
    def _from_row(cls, row) -> "Provider":
        return cls(
            id=row["id"],
            nombre=row["nombre"],
            identificador_fiscal=row["identificador_fiscal"],
            activo=bool(row["activo"]),
            fecha_alta=row["fecha_alta"],
        )


def _normalizar(nombre: str) -> str:
    return " ".join(nombre.strip().lower().split())


def create(nombre: str, identificador_fiscal: str | None = None) -> Provider:
    conn = get_connection()
    fecha_alta = datetime.now(UTC).isoformat()
    cursor = conn.execute(
        "INSERT INTO providers (nombre, identificador_fiscal, activo, fecha_alta) "
        "VALUES (?, ?, 1, ?)",
        (nombre, identificador_fiscal, fecha_alta),
    )
    conn.commit()
    return get_by_id(cursor.lastrowid)


def get_by_id(provider_id: int) -> Provider | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
    return Provider._from_row(row) if row else None


def get_by_nombre_normalizado(nombre: str) -> Provider | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM providers WHERE lower(trim(nombre)) = ?", (_normalizar(nombre),)
    ).fetchone()
    return Provider._from_row(row) if row else None


def list_all(activo: bool | None = None) -> list[Provider]:
    conn = get_connection()
    if activo is None:
        rows = conn.execute("SELECT * FROM providers ORDER BY nombre").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM providers WHERE activo = ? ORDER BY nombre", (int(activo),)
        ).fetchall()
    return [Provider._from_row(row) for row in rows]


def set_activo(provider_id: int, activo: bool) -> Provider | None:
    conn = get_connection()
    conn.execute("UPDATE providers SET activo = ? WHERE id = ?", (int(activo), provider_id))
    conn.commit()
    return get_by_id(provider_id)


def set_identificador_fiscal(provider_id: int, identificador_fiscal: str | None) -> Provider | None:
    conn = get_connection()
    conn.execute(
        "UPDATE providers SET identificador_fiscal = ? WHERE id = ?",
        (identificador_fiscal, provider_id),
    )
    conn.commit()
    return get_by_id(provider_id)
