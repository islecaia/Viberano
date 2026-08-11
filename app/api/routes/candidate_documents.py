"""Endpoints de contracts/api.md para revisar documentos candidatos (User Story 3, FR-010)."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.auth.session import get_current_user
from app.models import candidate_document as candidate_document_model
from app.services import attachment_store

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


class CandidateDetailResponse(BaseModel):
    id: int
    estado: str
    motivo_clasificacion: str
    remitente: str
    asunto: str
    fecha_correo: str
    adjunto_url: str


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


@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate(
    candidate_id: int, _persona_autorizada: str = Depends(get_current_user)
) -> CandidateDetailResponse:
    entry = candidate_document_model.get_with_email(candidate_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    doc = entry.documento
    return CandidateDetailResponse(
        id=doc.id,
        estado=doc.estado,
        motivo_clasificacion=doc.motivo_clasificacion,
        remitente=entry.correo_remitente,
        asunto=entry.correo_asunto,
        fecha_correo=entry.correo_fecha,
        adjunto_url=f"/api/candidate-documents/{doc.id}/attachment",
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
