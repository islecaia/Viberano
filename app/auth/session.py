"""Sesión mínima de persona autorizada (research.md §6, FR-001).

Cookie de servidor firmada con HMAC (sin dependencias externas): contiene el email de la
persona autorizada y una firma que impide falsificarla sin conocer SESSION_SECRET.
No implementa gestión de roles ni de cuentas múltiples — solo verifica pertenencia a
AUTHORIZED_ACCOUNTS.
"""

import hashlib
import hmac
import os

from fastapi import Cookie, HTTPException, status

SESSION_COOKIE_NAME = "invoice_manager_session"


def _secret() -> bytes:
    return os.environ.get("SESSION_SECRET", "changeme-generate-a-random-secret").encode("utf-8")


def _authorized_accounts() -> set[str]:
    raw = os.environ.get("AUTHORIZED_ACCOUNTS", "")
    return {email.strip().lower() for email in raw.split(",") if email.strip()}


def is_authorized(email: str) -> bool:
    return email.strip().lower() in _authorized_accounts()


def create_session_token(email: str) -> str:
    signature = hmac.new(_secret(), email.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{email}:{signature}"


def verify_session_token(token: str) -> str | None:
    """Devuelve el email si el token es válido y sigue autorizado; None en caso contrario."""
    if ":" not in token:
        return None
    email, signature = token.rsplit(":", 1)
    expected = hmac.new(_secret(), email.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    if not is_authorized(email):
        return None
    return email


def get_current_user(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> str:
    """Dependencia de FastAPI: exige sesión autorizada válida (FR-001) o responde 401."""
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    email = verify_session_token(session)
    if email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida")
    return email
