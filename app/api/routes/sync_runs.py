"""Endpoints de contracts/api.md: POST /api/mailbox-accounts/{id}/sync, GET /api/sync-runs/{id}.

Nota de implementación: esta versión ejecuta la sincronización de forma síncrona dentro de la
propia petición (adecuado al volumen esperado, research.md §7) en vez de encolarla en segundo
plano; por eso el `estado` devuelto puede llegar ya como `completada` o `interrumpida` en la
respuesta 202, no solo `en_curso`. `GET /api/sync-runs/{id}` sigue siendo válido para consultarla
después.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.session import get_current_user
from app.models import sync_run as sync_run_model
from app.services.sync_service import (
    CuentaNoDisponibleError,
    SincronizacionEnCursoError,
    start_sync,
)

mailbox_sync_router = APIRouter(prefix="/mailbox-accounts", tags=["sync"])
sync_runs_router = APIRouter(prefix="/sync-runs", tags=["sync"])


class SyncRunResponse(BaseModel):
    id: int
    estado: str
    fecha_inicio: str
    fecha_fin: str | None = None
    correos_procesados: int
    candidatos_generados: int


@mailbox_sync_router.post(
    "/{account_id}/sync", status_code=status.HTTP_202_ACCEPTED, response_model=SyncRunResponse
)
def trigger_sync(
    account_id: int, persona_autorizada: str = Depends(get_current_user)
) -> SyncRunResponse:
    try:
        sync_run = start_sync(cuenta_id=account_id, persona_autorizada=persona_autorizada)
    except SincronizacionEnCursoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CuentaNoDisponibleError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return SyncRunResponse(**sync_run.__dict__)


@sync_runs_router.get("/{sync_id}", response_model=SyncRunResponse)
def get_sync_run(
    sync_id: int, _persona_autorizada: str = Depends(get_current_user)
) -> SyncRunResponse:
    sync_run = sync_run_model.get_by_id(sync_id)
    if sync_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sincronización no encontrada"
        )
    return SyncRunResponse(**sync_run.__dict__)
