"""Endpoints de contracts/api.md para el catálogo de proveedores (User Story 2)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.session import get_current_user
from app.models import provider as provider_model

router = APIRouter(prefix="/providers", tags=["providers"])


class ProviderResponse(BaseModel):
    id: int
    nombre: str
    identificador_fiscal: str | None
    activo: bool


class CreateProviderRequest(BaseModel):
    nombre: str
    identificador_fiscal: str | None = None


class UpdateProviderRequest(BaseModel):
    activo: bool


class ProviderListResponse(BaseModel):
    items: list[ProviderResponse]


def _to_response(provider: provider_model.Provider) -> ProviderResponse:
    return ProviderResponse(
        id=provider.id,
        nombre=provider.nombre,
        identificador_fiscal=provider.identificador_fiscal,
        activo=provider.activo,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProviderResponse)
def create_provider(
    payload: CreateProviderRequest, _persona_autorizada: str = Depends(get_current_user)
) -> ProviderResponse:
    if provider_model.get_by_nombre_normalizado(payload.nombre) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un proveedor con el nombre '{payload.nombre}'",
        )
    provider = provider_model.create(payload.nombre, payload.identificador_fiscal)
    return _to_response(provider)


@router.get("", response_model=ProviderListResponse)
def list_providers(
    activo: bool | None = None, _persona_autorizada: str = Depends(get_current_user)
) -> ProviderListResponse:
    providers = provider_model.list_all(activo=activo)
    return ProviderListResponse(items=[_to_response(p) for p in providers])


@router.patch("/{provider_id}", response_model=ProviderResponse)
def update_provider(
    provider_id: int,
    payload: UpdateProviderRequest,
    _persona_autorizada: str = Depends(get_current_user),
) -> ProviderResponse:
    if provider_model.get_by_id(provider_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado"
        )
    provider = provider_model.set_activo(provider_id, payload.activo)
    return _to_response(provider)
