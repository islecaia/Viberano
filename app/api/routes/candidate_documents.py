"""Endpoints de contracts/api.md para revisar documentos candidatos.

Ampliado por specs/002-validacion-archivado-facturas/ con `POST .../validate` (User Story 1) y
`POST .../reclassify` (User Story 3); las rutas originales son de la feature 001 (User Story 3
allí, FR-010).
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.auth.session import get_current_user
from app.models import bank_movement as bank_movement_model
from app.models import candidate_document as candidate_document_model
from app.models import provider as provider_model
from app.models import reconciliation_candidate as reconciliation_candidate_model
from app.services import attachment_store
from app.services.validation_service import (
    CampoInvalidoError,
    ProveedorInactivoError,
    validate_and_archive,
)

router = APIRouter(prefix="/candidate-documents", tags=["candidate-documents"])

_CONTENT_TYPES = {"pdf": "application/pdf", "jpg": "image/jpeg", "png": "image/png"}


class CandidateListItem(BaseModel):
    id: int
    estado: str
    remitente: str
    asunto: str
    fecha_correo: str
    formato: str
    nombre_archivo_original: str


class CandidateListResponse(BaseModel):
    items: list[CandidateListItem]
    total: int


class ProviderRef(BaseModel):
    id: int
    nombre: str


class Sugerencia(BaseModel):
    proveedor_nombre: str | None = None
    proveedor_id_coincidente: int | None = None
    fecha_factura: str | None = None
    numero_factura: str | None = None
    total: float | None = None


class ReconciledMovementRef(BaseModel):
    id: int
    fecha: str
    importe: float
    concepto: str


class CandidateDetailResponse(BaseModel):
    id: int
    estado: str
    motivo_clasificacion: str
    remitente: str
    asunto: str
    fecha_correo: str
    adjunto_url: str
    proveedor: ProviderRef | None = None
    fecha_factura: str | None = None
    numero_factura: str | None = None
    total: float | None = None
    es_nota_credito: bool = False
    validado_por: str | None = None
    fecha_validacion: str | None = None
    sugerencia: Sugerencia | None = None
    estado_conciliacion: str | None = None
    movimiento_conciliado: ReconciledMovementRef | None = None
    conciliacion_candidatos: list[ReconciledMovementRef] | None = None


class ValidateRequest(BaseModel):
    fecha_factura: str
    numero_factura: str
    total: float
    es_nota_credito: bool = False
    proveedor_id: int | None = None
    proveedor_nombre_nuevo: str | None = None
    proveedor_nif_nuevo: str | None = None


class ReclassifyRequest(BaseModel):
    estado: str


class ReclassifyResponse(BaseModel):
    id: int
    estado: str


class ReconcileRequest(BaseModel):
    movimiento_id: int | None = None


class ReconcileResponse(BaseModel):
    id: int
    estado_conciliacion: str
    movimiento_id: int | None = None


def _to_list_item(entry) -> CandidateListItem:
    doc = entry.documento
    return CandidateListItem(
        id=doc.id,
        estado=doc.estado,
        remitente=entry.correo_remitente,
        asunto=entry.correo_asunto,
        fecha_correo=entry.correo_fecha,
        formato=doc.formato,
        nombre_archivo_original=doc.nombre_archivo_original,
    )


@router.get("", response_model=CandidateListResponse)
def list_candidates(
    estado: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    _persona_autorizada: str = Depends(get_current_user),
) -> CandidateListResponse:
    entries = candidate_document_model.list_with_email(estado=estado, desde=desde, hasta=hasta)
    items = [_to_list_item(entry) for entry in entries]
    return CandidateListResponse(items=items, total=len(items))


def _build_sugerencia(doc) -> Sugerencia | None:
    """FR-008 de specs/003-sugerencia-datos-factura/: sin sugerencia fuera de REVISIÓN MANUAL."""
    if doc.estado != candidate_document_model.ESTADO_REVISION_MANUAL:
        return None
    campos = (
        doc.sugerido_proveedor_nombre,
        doc.sugerido_fecha_factura,
        doc.sugerido_numero_factura,
        doc.sugerido_total,
    )
    if all(campo is None for campo in campos):
        return None
    proveedor_coincidente = None
    if doc.sugerido_proveedor_nombre:
        # research.md §6 de specs/003-sugerencia-datos-factura/: se resuelve en el momento de
        # mostrar la pantalla, no se persiste — el catálogo puede haber cambiado desde entonces.
        coincidencia = provider_model.get_by_nombre_normalizado(doc.sugerido_proveedor_nombre)
        proveedor_coincidente = coincidencia.id if coincidencia else None
    return Sugerencia(
        proveedor_nombre=doc.sugerido_proveedor_nombre,
        proveedor_id_coincidente=proveedor_coincidente,
        fecha_factura=doc.sugerido_fecha_factura,
        numero_factura=doc.sugerido_numero_factura,
        total=doc.sugerido_total,
    )


def _to_movement_ref(movimiento) -> ReconciledMovementRef:
    return ReconciledMovementRef(
        id=movimiento.id,
        fecha=movimiento.fecha,
        importe=movimiento.importe,
        concepto=movimiento.concepto,
    )


def _to_detail_response(entry) -> CandidateDetailResponse:
    doc = entry.documento
    proveedor_ref = None
    if doc.proveedor_id is not None:
        proveedor = provider_model.get_by_id(doc.proveedor_id)
        if proveedor is not None:
            proveedor_ref = ProviderRef(id=proveedor.id, nombre=proveedor.nombre)

    movimiento_conciliado = None
    if doc.movimiento_bancario_id is not None:
        movimiento = bank_movement_model.get_by_id(doc.movimiento_bancario_id)
        if movimiento is not None:
            movimiento_conciliado = _to_movement_ref(movimiento)

    conciliacion_candidatos = None
    if doc.estado_conciliacion == "PENDIENTE REVISIÓN CONCILIACIÓN":
        candidatos = reconciliation_candidate_model.list_for_documento(doc.id)
        movimientos = [bank_movement_model.get_by_id(c.movimiento_id) for c in candidatos]
        conciliacion_candidatos = [_to_movement_ref(m) for m in movimientos if m is not None]

    return CandidateDetailResponse(
        id=doc.id,
        estado=doc.estado,
        motivo_clasificacion=doc.motivo_clasificacion,
        remitente=entry.correo_remitente,
        asunto=entry.correo_asunto,
        fecha_correo=entry.correo_fecha,
        adjunto_url=f"/api/candidate-documents/{doc.id}/attachment",
        proveedor=proveedor_ref,
        fecha_factura=doc.fecha_factura,
        numero_factura=doc.numero_factura,
        total=doc.total,
        es_nota_credito=doc.es_nota_credito,
        validado_por=doc.validado_por,
        fecha_validacion=doc.fecha_validacion,
        sugerencia=_build_sugerencia(doc),
        estado_conciliacion=doc.estado_conciliacion,
        movimiento_conciliado=movimiento_conciliado,
        conciliacion_candidatos=conciliacion_candidatos,
    )


@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate(
    candidate_id: int, _persona_autorizada: str = Depends(get_current_user)
) -> CandidateDetailResponse:
    entry = candidate_document_model.get_with_email(candidate_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    return _to_detail_response(entry)


@router.post("/{candidate_id}/validate", response_model=CandidateDetailResponse)
def validate_candidate(
    candidate_id: int,
    payload: ValidateRequest,
    persona_autorizada: str = Depends(get_current_user),
) -> CandidateDetailResponse:
    if candidate_document_model.get_by_id(candidate_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    try:
        validate_and_archive(
            candidate_id=candidate_id,
            fecha_factura=payload.fecha_factura,
            numero_factura=payload.numero_factura,
            total=payload.total,
            es_nota_credito=payload.es_nota_credito,
            validado_por=persona_autorizada,
            proveedor_id=payload.proveedor_id,
            proveedor_nombre_nuevo=payload.proveedor_nombre_nuevo,
            proveedor_nif_nuevo=payload.proveedor_nif_nuevo,
        )
    except CampoInvalidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except ProveedorInactivoError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(exc), "proveedor_id": exc.proveedor_id},
        ) from exc
    except candidate_document_model.DocumentoNoEnRevisionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except candidate_document_model.ArchivadoDuplicadoError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(exc), "documento_id": exc.documento_id},
        ) from exc

    entry = candidate_document_model.get_with_email(candidate_id)
    return _to_detail_response(entry)


@router.post("/{candidate_id}/reclassify", response_model=ReclassifyResponse)
def reclassify_candidate(
    candidate_id: int,
    payload: ReclassifyRequest,
    _persona_autorizada: str = Depends(get_current_user),
) -> ReclassifyResponse:
    if payload.estado not in candidate_document_model.ESTADOS_RECLASIFICABLES:
        opciones = ", ".join(candidate_document_model.ESTADOS_RECLASIFICABLES)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"estado debe ser uno de: {opciones}",
        )
    if candidate_document_model.get_by_id(candidate_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado"
        )
    try:
        doc = candidate_document_model.reclassify(candidate_id, payload.estado)
    except candidate_document_model.DocumentoNoEnRevisionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ReclassifyResponse(id=doc.id, estado=doc.estado)


@router.post("/{candidate_id}/reconcile", response_model=ReconcileResponse)
def reconcile_candidate(
    candidate_id: int,
    payload: ReconcileRequest,
    _persona_autorizada: str = Depends(get_current_user),
) -> ReconcileResponse:
    """User Story 2 de specs/004-conciliacion-bancaria/ (FR-006): resuelve manualmente un
    documento PENDIENTE REVISIÓN CONCILIACIÓN, eligiendo un candidato o descartándolos todos."""
    doc = candidate_document_model.get_by_id(candidate_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado"
        )
    if doc.estado_conciliacion != "PENDIENTE REVISIÓN CONCILIACIÓN":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El documento no está pendiente de revisión de conciliación",
        )

    candidatos = reconciliation_candidate_model.list_for_documento(candidate_id)
    ids_candidatos = {c.movimiento_id for c in candidatos}

    if payload.movimiento_id is not None and payload.movimiento_id not in ids_candidatos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{payload.movimiento_id} no es uno de los candidatos de este documento",
        )

    try:
        if payload.movimiento_id is not None:
            actualizado = candidate_document_model.mark_conciliada(
                candidate_id, payload.movimiento_id, doc.conciliado_con_extracto_id
            )
        else:
            actualizado = candidate_document_model.mark_no_encontrada(
                candidate_id, doc.conciliado_con_extracto_id
            )
    except candidate_document_model.MovimientoYaVinculadoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except candidate_document_model.ConciliacionYaResueltaError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    reconciliation_candidate_model.clear_for_documento(candidate_id)
    return ReconcileResponse(
        id=actualizado.id,
        estado_conciliacion=actualizado.estado_conciliacion,
        movimiento_id=actualizado.movimiento_bancario_id,
    )


@router.get("/{candidate_id}/attachment")
def get_candidate_attachment(
    candidate_id: int, _persona_autorizada: str = Depends(get_current_user)
) -> Response:
    doc = candidate_document_model.get_by_id(candidate_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    content = attachment_store.read_attachment(doc.archivo_adjunto_ref)
    return Response(content=content, media_type=_CONTENT_TYPES[doc.formato])
