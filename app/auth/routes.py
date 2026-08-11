"""Rutas de login/logout — fuera de /api/, no exigen sesión previa."""

import os
import secrets

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from app.auth.session import SESSION_COOKIE_NAME, create_session_token, is_authorized

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(payload: LoginRequest, response: Response) -> dict:
    expected_password = os.environ.get("APP_PASSWORD", "")
    if not is_authorized(payload.email) or not secrets.compare_digest(
        payload.password, expected_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas"
        )
    token = create_session_token(payload.email)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=True,
    )
    return {"email": payload.email}


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return {"ok": True}
