"""Modelo DocumentoCandidato (data-model.md § DocumentoCandidato de las features 001 y 002).

`estado` solo puede llegar a PROCESADA a través de `mark_procesada()` (FR-002 a FR-004,
Principio II) — nunca al crearse (`create()`, usado por la ingesta). PROCESADA, NO ES FACTURA,
FACTURA DE VENTA y DUPLICADO IGNORADO son estados finales dentro de esta feature (FR-011):
`mark_procesada()` y `reclassify()` exigen que el documento siga en REVISIÓN MANUAL.
"""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.session import get_connection

ESTADOS_VALIDOS = {"REVISIÓN MANUAL", "NO ES FACTURA", "FACTURA DE VENTA", "DUPLICADO IGNORADO"}
ESTADO_REVISION_MANUAL = "REVISIÓN MANUAL"
ESTADOS_RECLASIFICABLES = {"NO ES FACTURA", "FACTURA DE VENTA"}


class DocumentoNoEnRevisionError(Exception):
    """El documento ya no está en REVISIÓN MANUAL (ya resuelto, o condición de carrera)."""


class ArchivadoDuplicadoError(Exception):
    """Ya existe otro documento PROCESADA con el mismo proveedor + fecha + número (FR-009)."""

    def __init__(self, documento_id: int | None = None):
        self.documento_id = documento_id
        detalle = f" (documento {documento_id})" if documento_id else ""
        super().__init__(
            f"Ya existe otro documento PROCESADA con el mismo proveedor, fecha y número{detalle}"
        )


class ConciliacionYaResueltaError(Exception):
    """El documento no está PROCESADA sin conciliar (specs/004-conciliacion-bancaria/,
    research.md §4)."""


class MovimientoYaVinculadoError(Exception):
    """El movimiento bancario ya está vinculado a otra factura (índice único, Principio I)."""


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
    proveedor_id: int | None
    fecha_factura: str | None
    numero_factura: str | None
    total: float | None
    es_nota_credito: bool
    validado_por: str | None
    fecha_validacion: str | None
    sugerido_proveedor_nombre: str | None
    sugerido_fecha_factura: str | None
    sugerido_numero_factura: str | None
    sugerido_total: float | None
    estado_conciliacion: str | None
    movimiento_bancario_id: int | None
    conciliado_con_extracto_id: int | None

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
            proveedor_id=row["proveedor_id"],
            fecha_factura=row["fecha_factura"],
            numero_factura=row["numero_factura"],
            total=row["total"],
            es_nota_credito=bool(row["es_nota_credito"]),
            validado_por=row["validado_por"],
            fecha_validacion=row["fecha_validacion"],
            sugerido_proveedor_nombre=row["sugerido_proveedor_nombre"],
            sugerido_fecha_factura=row["sugerido_fecha_factura"],
            sugerido_numero_factura=row["sugerido_numero_factura"],
            sugerido_total=row["sugerido_total"],
            estado_conciliacion=row["estado_conciliacion"],
            movimiento_bancario_id=row["movimiento_bancario_id"],
            conciliado_con_extracto_id=row["conciliado_con_extracto_id"],
        )


def create(
    correo_id: int,
    archivo_adjunto_ref: str,
    nombre_archivo_original: str,
    formato: str,
    estado: str,
    motivo_clasificacion: str,
    sugerido_proveedor_nombre: str | None = None,
    sugerido_fecha_factura: str | None = None,
    sugerido_numero_factura: str | None = None,
    sugerido_total: float | None = None,
) -> CandidateDocument:
    """Las sugerencias (specs/003-sugerencia-datos-factura/) se guardan una única vez al crear el
    documento; no cambian después (research.md §2 de esa feature)."""
    if estado not in ESTADOS_VALIDOS:
        raise ValueError(f"Estado no permitido en esta feature: {estado}")
    conn = get_connection()
    fecha_creacion = datetime.now(UTC).isoformat()
    cursor = conn.execute(
        """
        INSERT INTO candidate_documents
            (correo_id, archivo_adjunto_ref, nombre_archivo_original, formato, estado,
             motivo_clasificacion, fecha_creacion, sugerido_proveedor_nombre,
             sugerido_fecha_factura, sugerido_numero_factura, sugerido_total)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            correo_id,
            archivo_adjunto_ref,
            nombre_archivo_original,
            formato,
            estado,
            motivo_clasificacion,
            fecha_creacion,
            sugerido_proveedor_nombre,
            sugerido_fecha_factura,
            sugerido_numero_factura,
            sugerido_total,
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


def list_procesada_sin_conciliar(fecha_inicio: str, fecha_fin: str) -> list[CandidateDocument]:
    """FR-002/FR-012 de specs/004-conciliacion-bancaria/: facturas PROCESADA dentro del periodo
    del extracto que todavía no se han evaluado en ninguna conciliación."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM candidate_documents
        WHERE estado = 'PROCESADA' AND estado_conciliacion IS NULL
              AND fecha_factura BETWEEN ? AND ?
        """,
        (fecha_inicio, fecha_fin),
    ).fetchall()
    return [CandidateDocument._from_row(row) for row in rows]


def list_by_extracto(extracto_id: int, estado_conciliacion: str) -> list[CandidateDocument]:
    """Facturas cuyo `estado_conciliacion` actual proviene de este extracto (contracts/api.md
    de specs/004-conciliacion-bancaria/, GET /api/reconciliations/{id})."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM candidate_documents
        WHERE conciliado_con_extracto_id = ? AND estado_conciliacion = ?
        """,
        (extracto_id, estado_conciliacion),
    ).fetchall()
    return [CandidateDocument._from_row(row) for row in rows]


def count_procesada_por_mes(fecha_inicio: str, fecha_fin: str) -> list[dict]:
    """FR-002/FR-003/FR-004 de specs/005-volumen-mensual-facturas/: recuento de facturas
    PROCESADA agrupado por año-mes de `fecha_factura`, dentro de `[fecha_inicio, fecha_fin]`
    (formato `YYYY-MM-DD`). Solo devuelve meses con al menos una factura — el mes en 0 lo
    completa metrics_service (FR-005)."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT strftime('%Y-%m', fecha_factura) AS mes, COUNT(*) AS total
        FROM candidate_documents
        WHERE estado = 'PROCESADA' AND fecha_factura BETWEEN ? AND ?
        GROUP BY mes
        """,
        (fecha_inicio, fecha_fin),
    ).fetchall()
    return [{"mes": row["mes"], "total": row["total"]} for row in rows]


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


def find_procesada_duplicado(
    proveedor_id: int, fecha_factura: str, numero_factura: str
) -> CandidateDocument | None:
    """Comprobación previa (para dar un mensaje con el id en conflicto, contracts/api.md);
    la garantía real contra condiciones de carrera la da el índice único (FR-009)."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT * FROM candidate_documents
        WHERE estado = 'PROCESADA' AND proveedor_id = ? AND fecha_factura = ?
              AND numero_factura = ?
        """,
        (proveedor_id, fecha_factura, numero_factura),
    ).fetchone()
    return CandidateDocument._from_row(row) if row else None


def mark_procesada(
    candidate_id: int,
    proveedor_id: int,
    fecha_factura: str,
    numero_factura: str,
    total: float,
    es_nota_credito: bool,
    validado_por: str,
) -> CandidateDocument:
    """FR-002 a FR-004, FR-008: transiciona a PROCESADA solo si sigue en REVISIÓN MANUAL.

    Lanza DocumentoNoEnRevisionError si ya no está en REVISIÓN MANUAL (resuelto por otra persona
    o condición de carrera, FR-011) o ArchivadoDuplicadoError si viola el índice único de
    data-model.md (FR-009).
    """
    conn = get_connection()
    fecha_validacion = datetime.now(UTC).isoformat()
    try:
        cursor = conn.execute(
            """
            UPDATE candidate_documents
            SET estado = 'PROCESADA', proveedor_id = ?, fecha_factura = ?, numero_factura = ?,
                total = ?, es_nota_credito = ?, validado_por = ?, fecha_validacion = ?
            WHERE id = ? AND estado = ?
            """,
            (
                proveedor_id,
                fecha_factura,
                numero_factura,
                total,
                int(es_nota_credito),
                validado_por,
                fecha_validacion,
                candidate_id,
                ESTADO_REVISION_MANUAL,
            ),
        )
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ArchivadoDuplicadoError() from exc

    if cursor.rowcount == 0:
        conn.rollback()
        raise DocumentoNoEnRevisionError(
            f"El documento {candidate_id} ya no está en {ESTADO_REVISION_MANUAL}"
        )
    conn.commit()
    return get_by_id(candidate_id)


_CONCILIABLE_DESDE = (
    "(estado_conciliacion IS NULL OR estado_conciliacion = 'PENDIENTE REVISIÓN CONCILIACIÓN')"
)


def _raise_no_conciliable(documento_id: int) -> None:
    raise ConciliacionYaResueltaError(f"El documento {documento_id} no admite conciliarse ahora")


def mark_conciliada(documento_id: int, movimiento_id: int, extracto_id: int) -> CandidateDocument:
    """FR-003, FR-006 de specs/004-conciliacion-bancaria/: vincula la factura a un movimiento
    bancario. Válido tanto desde `estado_conciliacion IS NULL` (conciliación automática, único
    candidato) como desde `'PENDIENTE REVISIÓN CONCILIACIÓN'` (resolución manual, FR-006)."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            f"""
            UPDATE candidate_documents
            SET estado_conciliacion = 'CONCILIADA', movimiento_bancario_id = ?,
                conciliado_con_extracto_id = ?
            WHERE id = ? AND estado = 'PROCESADA' AND {_CONCILIABLE_DESDE}
            """,
            (movimiento_id, extracto_id, documento_id),
        )
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise MovimientoYaVinculadoError(
            f"El movimiento {movimiento_id} ya está vinculado a otra factura"
        ) from exc
    if cursor.rowcount == 0:
        conn.rollback()
        _raise_no_conciliable(documento_id)
    conn.commit()
    return get_by_id(documento_id)


def mark_no_encontrada(documento_id: int, extracto_id: int) -> CandidateDocument:
    """FR-004, FR-006: nunca 'impagada' — solo 'no encontrada en el extracto' (Principio VI).
    Válido desde `estado_conciliacion IS NULL` o desde `'PENDIENTE REVISIÓN CONCILIACIÓN'`."""
    conn = get_connection()
    cursor = conn.execute(
        f"""
        UPDATE candidate_documents
        SET estado_conciliacion = 'NO ENCONTRADA EN EXTRACTO', conciliado_con_extracto_id = ?
        WHERE id = ? AND estado = 'PROCESADA' AND {_CONCILIABLE_DESDE}
        """,
        (extracto_id, documento_id),
    )
    if cursor.rowcount == 0:
        conn.rollback()
        _raise_no_conciliable(documento_id)
    conn.commit()
    return get_by_id(documento_id)


def mark_pendiente_revision(documento_id: int, extracto_id: int) -> CandidateDocument:
    """FR-005: varios candidatos igual de plausibles — nunca se elige automáticamente por uno."""
    conn = get_connection()
    cursor = conn.execute(
        """
        UPDATE candidate_documents
        SET estado_conciliacion = 'PENDIENTE REVISIÓN CONCILIACIÓN', conciliado_con_extracto_id = ?
        WHERE id = ? AND estado = 'PROCESADA' AND estado_conciliacion IS NULL
        """,
        (extracto_id, documento_id),
    )
    if cursor.rowcount == 0:
        conn.rollback()
        _raise_no_conciliable(documento_id)
    conn.commit()
    return get_by_id(documento_id)


def reclassify(candidate_id: int, estado: str) -> CandidateDocument:
    """FR-007: reclasifica un documento en REVISIÓN MANUAL como NO ES FACTURA o FACTURA DE VENTA."""
    if estado not in ESTADOS_RECLASIFICABLES:
        raise ValueError(f"Estado no permitido para reclasificar: {estado}")

    conn = get_connection()
    cursor = conn.execute(
        "UPDATE candidate_documents SET estado = ? WHERE id = ? AND estado = ?",
        (estado, candidate_id, ESTADO_REVISION_MANUAL),
    )
    if cursor.rowcount == 0:
        conn.rollback()
        raise DocumentoNoEnRevisionError(
            f"El documento {candidate_id} ya no está en {ESTADO_REVISION_MANUAL}"
        )
    conn.commit()
    return get_by_id(candidate_id)
