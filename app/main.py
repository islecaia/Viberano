"""Arranque de FastAPI (M1).

Toda ruta bajo /api/ exige sesión autorizada mediante la dependencia declarada en
app.api.routes.api_router (T008, FR-001). Las rutas de /auth/ quedan fuera de esa exigencia,
ya que son las que permiten iniciar sesión.
"""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from app.api.routes import api_router
from app.auth.routes import router as auth_router
from app.db.session import init_db
from app.web import router as web_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("invoice_manager")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

app = FastAPI(title="Invoice Manager")


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("Base de datos inicializada")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    # No se registra el cuerpo de la petición: podría contener credenciales (research.md §6).
    logger.warning("HTTP %s en %s: %s", exc.status_code, request.url.path, exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error no controlado en %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Error interno"})


app.include_router(auth_router)
app.include_router(web_router)
app.include_router(api_router)
