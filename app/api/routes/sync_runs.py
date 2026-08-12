"""Endpoints de contracts/api.md: analizar un lote, ejecutarlo (aprobar/reanudar/reintentar),
consultarlo.

Nota de implementación: tanto `analizar_lote()` como `ejecutar_lote()` se ejecutan de forma
síncrona dentro de la propia petición (adecuado al volumen esperado, research.md §7 de la
feature 001) en vez de encolarse en segundo plano.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.session import get_current_user
from app.models import ingested_email as ingested_email_model
from app.models import sync_run as sync_run_model
from app.models.sync_run import SyncRun
from app.services.mailbox.base import MailboxConnectionError
from app.services.sync_service import (
    CuentaNoDisponibleError,
    LoteNoEncontradoError,
    NadaQueEjecutarError,
    SincronizacionEnCursoError,
    analizar_lote,
    ejecutar_lote,
)

mailbox_sync_router = APIRouter(prefix="/mailbox-accounts", tags=["sync"])
sync_runs_router = APIRouter(prefix="/sync-runs", tags=["sync"])


class CorreoFallidoRef(BaseModel):
    id: int
    remitente: str
    asunto: str
    motivo_fallo: str | None = None


class SyncRunResponse(BaseModel):
    id: int
    estado: str
    fecha_inicio: str
    fecha_fin: str | None = None
    correos_procesados: int
    candidatos_generados: int
    correos_nuevos_detectados: int
    correos_con_adjuntos_candidatos: int
    correos_fallidos: list[CorreoFallidoRef] = []


class AnalisisResponse(BaseModel):
    lote: SyncRunResponse | None = None


def _to_response(sync_run: SyncRun) -> SyncRunResponse:
    fallidos = [
        CorreoFallidoRef(
            id=correo.id,
            remitente=correo.remitente,
            asunto=correo.asunto,
            motivo_fallo=correo.motivo_fallo,
        )
        for correo in ingested_email_model.list_fallidos(sync_run.id)
    ]
    return SyncRunResponse(**sync_run.__dict__, correos_fallidos=fallidos)


@mailbox_sync_router.post(
    "/{account_id}/sync", status_code=status.HTTP_202_ACCEPTED, response_model=AnalisisResponse
)
def trigger_analisis(
    account_id: int, persona_autorizada: str = Depends(get_current_user)
) -> AnalisisResponse:
    """`lote` es `null` cuando el análisis no encuentra ningún correo con adjunto candidato: en
    ese caso no se crea ningún registro de lote y la cuenta queda libre de inmediato para una
    nueva sincronización (sync_service.analizar_lote())."""
    try:
        sync_run = analizar_lote(cuenta_id=account_id, persona_autorizada=persona_autorizada)
    except SincronizacionEnCursoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CuentaNoDisponibleError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except MailboxConnectionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    if sync_run is None:
        return AnalisisResponse(lote=None)
    return AnalisisResponse(lote=_to_response(sync_run))


@mailbox_sync_router.post(
    "/{account_id}/sync/{sync_run_id}/execute", response_model=SyncRunResponse
)
def trigger_ejecucion(
    account_id: int,
    sync_run_id: int,
    persona_autorizada: str = Depends(get_current_user),
) -> SyncRunResponse:
    sync_run_actual = sync_run_model.get_by_id(sync_run_id)
    if sync_run_actual is None or sync_run_actual.cuenta_id != account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado")
    try:
        sync_run = ejecutar_lote(sync_run_id=sync_run_id, persona_autorizada=persona_autorizada)
    except LoteNoEncontradoError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except NadaQueEjecutarError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return _to_response(sync_run)


@sync_runs_router.get("/{sync_id}", response_model=SyncRunResponse)
def get_sync_run(
    sync_id: int, _persona_autorizada: str = Depends(get_current_user)
) -> SyncRunResponse:
    sync_run = sync_run_model.get_by_id(sync_id)
    if sync_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sincronización no encontrada"
        )
    return _to_response(sync_run)
