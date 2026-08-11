"""Endpoints de contracts/api.md: POST /api/mailbox-accounts, GET /api/mailbox-accounts/current."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.session import get_current_user
from app.models import mailbox_account as mailbox_account_model
from app.services.mailbox_account_service import (
    PROVEEDORES_VALIDOS,
    CredencialesInvalidasError,
    CuentaYaConectadaError,
    connect_account,
)

router = APIRouter(prefix="/mailbox-accounts", tags=["mailbox-accounts"])


class ConnectMailboxRequest(BaseModel):
    proveedor: str
    email_address: str
    credenciales: dict


class MailboxAccountResponse(BaseModel):
    # T036: campos listados explícitamente (sin `credenciales_ref`) — Pydantic descarta
    # cualquier extra pasado vía **account.__dict__, así que el secreto nunca sale en JSON.
    id: int
    proveedor: str
    email_address: str
    estado: str
    fecha_conexion: str
    ultima_sincronizacion_cursor: str | None = None


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MailboxAccountResponse)
def connect_mailbox(
    payload: ConnectMailboxRequest, persona_autorizada: str = Depends(get_current_user)
) -> MailboxAccountResponse:
    if payload.proveedor not in PROVEEDORES_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Proveedor no soportado: {payload.proveedor}",
        )
    try:
        account = connect_account(
            persona_autorizada=persona_autorizada,
            proveedor=payload.proveedor,
            email_address=payload.email_address,
            credenciales=payload.credenciales,
        )
    except CuentaYaConectadaError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CredencialesInvalidasError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return MailboxAccountResponse(**account.__dict__)


@router.get("/current", response_model=MailboxAccountResponse)
def get_current_mailbox(
    persona_autorizada: str = Depends(get_current_user),
) -> MailboxAccountResponse:
    account = mailbox_account_model.get_for_persona(persona_autorizada)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ninguna cuenta conectada todavía"
        )
    return MailboxAccountResponse(**account.__dict__)
