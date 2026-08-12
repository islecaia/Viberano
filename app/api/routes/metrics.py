"""Endpoint de contracts/api.md para el volumen mensual de facturas.

specs/005-volumen-mensual-facturas/. Es de solo lectura (FR-009): no crea, modifica ni archiva
ninguna factura.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.session import get_current_user
from app.models import mailbox_account as mailbox_account_model
from app.services import metrics_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


class MesRecuento(BaseModel):
    mes: str
    total: int
    completo: bool


class VolumenMensualResponse(BaseModel):
    desde: str
    hasta: str
    meses: list[MesRecuento]
    media_meses_completos: float | None
    media_con_mes_parcial: float | None


@router.get("/volumen-mensual", response_model=VolumenMensualResponse)
def volumen_mensual(
    desde: str | None = None,
    hasta: str | None = None,
    persona_autorizada: str = Depends(get_current_user),
) -> VolumenMensualResponse:
    try:
        desde_final, hasta_final = metrics_service.resolver_periodo(desde, hasta)
    except metrics_service.PeriodoInvalidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    cuenta = mailbox_account_model.get_for_persona(persona_autorizada)
    resultado = metrics_service.volumen_mensual(
        desde_final,
        hasta_final,
        fecha_conexion_cuenta=cuenta.fecha_conexion if cuenta else None,
    )
    return VolumenMensualResponse(**resultado)
