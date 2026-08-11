"""Modelo DocumentoCandidato (data-model.md § DocumentoCandidato).

`estado` nunca puede ser PROCESADA en esta feature (FR-007, FR-011, Principio II) — esa
transición pertenece a la futura feature de validación y archivado.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.session import get_connection

ESTADOS_VALIDOS = {"REVISIÓN MANUAL", "NO ES FACTURA", "FACTURA DE VENTA", "DUPLICADO IGNORADO"}


@dataclass(frozen=True)
class CandidateDocument:
    id: int
    correo_id: int
    archivo_adjunto_ref: str
    nombre_archivo_original: str
    formato: str
    estado: str
    motivo_clasificacion: str
    fecha_creacion: str

    @classmethod
    def _from_row(cls, row) -> "CandidateDocument":
        return cls(
            id=row["id"],
            correo_id=row["correo_id"],
            archivo_adjunto_ref=row["archivo_adjunto_ref"],
            nombre_archivo_original=row["nombre_archivo_original"],
            formato=row["formato"],
            estado=row["estado"],
            motivo_clasificacion=row["motivo_clasificacion"],
            fecha_creacion=row["fecha_creacion"],
        )


def create(
    correo_id: int,
    archivo_adjunto_ref: str,
    nombre_archivo_original: str,
    formato: str,
    estado: str,
    motivo_clasificacion: str,
) -> CandidateDocument:
    if estado not in ESTADOS_VALIDOS:
        raise ValueError(f"Estado no permitido en esta feature: {estado}")
    conn = get_connection()
    fecha_creacion = datetime.now(UTC).isoformat()
    cursor = conn.execute(
        """
        INSERT INTO candidate_documents
            (correo_id, archivo_adjunto_ref, nombre_archivo_original, formato, estado,
             motivo_clasificacion, fecha_creacion)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            correo_id,
            archivo_adjunto_ref,
            nombre_archivo_original,
            formato,
            estado,
            motivo_clasificacion,
            fecha_creacion,
        ),
    )
    conn.commit()
    return get_by_id(cursor.lastrowid)


def get_by_id(candidate_id: int) -> CandidateDocument | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM candidate_documents WHERE id = ?", (candidate_id,)
    ).fetchone()
    return CandidateDocument._from_row(row) if row else None


def list_all(estado: str | None = None) -> list[CandidateDocument]:
    conn = get_connection()
    if estado:
        rows = conn.execute(
            "SELECT * FROM candidate_documents WHERE estado = ? ORDER BY fecha_creacion DESC",
            (estado,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM candidate_documents ORDER BY fecha_creacion DESC"
        ).fetchall()
    return [CandidateDocument._from_row(row) for row in rows]


_JOIN_EMAIL_SQL = """
    SELECT cd.*, ie.remitente AS correo_remitente, ie.asunto AS correo_asunto,
           ie.fecha_correo AS correo_fecha
    FROM candidate_documents cd
    JOIN ingested_emails ie ON ie.id = cd.correo_id
"""


@dataclass(frozen=True)
class CandidateDocumentWithEmail:
    documento: CandidateDocument
    correo_remitente: str
    correo_asunto: str
    correo_fecha: str

    @classmethod
    def _from_row(cls, row) -> "CandidateDocumentWithEmail":
        return cls(
            documento=CandidateDocument._from_row(row),
            correo_remitente=row["correo_remitente"],
            correo_asunto=row["correo_asunto"],
            correo_fecha=row["correo_fecha"],
        )


def list_with_email(
    estado: str | None = None, desde: str | None = None, hasta: str | None = None
) -> list[CandidateDocumentWithEmail]:
    conn = get_connection()
    clauses = []
    params: list[str] = []
    if estado:
        clauses.append("cd.estado = ?")
        params.append(estado)
    if desde:
        clauses.append("ie.fecha_correo >= ?")
        params.append(desde)
    if hasta:
        clauses.append("ie.fecha_correo <= ?")
        params.append(hasta)
    sql = _JOIN_EMAIL_SQL
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY cd.fecha_creacion DESC"
    rows = conn.execute(sql, params).fetchall()
    return [CandidateDocumentWithEmail._from_row(row) for row in rows]


def get_with_email(candidate_id: int) -> CandidateDocumentWithEmail | None:
    conn = get_connection()
    row = conn.execute(_JOIN_EMAIL_SQL + " WHERE cd.id = ?", (candidate_id,)).fetchone()
    return CandidateDocumentWithEmail._from_row(row) if row else None
