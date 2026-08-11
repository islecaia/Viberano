"""Páginas HTML server-rendered (fuera de /api/): no exigen sesión vía 401 JSON, sino redirect."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.session import verify_session_token
from app.models import candidate_document as candidate_document_model
from app.models import mailbox_account as mailbox_account_model

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _current_user_or_none(request: Request) -> str | None:
    token = request.cookies.get("invoice_manager_session")
    if not token:
        return None
    return verify_session_token(token)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.get("/mailbox/connect", response_class=HTMLResponse)
def mailbox_connect_page(request: Request):
    persona = _current_user_or_none(request)
    if persona is None:
        return RedirectResponse(url="/login")
    cuenta = mailbox_account_model.get_for_persona(persona)
    return templates.TemplateResponse(
        request, "mailbox_connect.html", {"cuenta": cuenta, "active_tab": "facturas"}
    )


@router.get("/facturas", response_class=HTMLResponse)
def facturas_page(request: Request):
    persona = _current_user_or_none(request)
    if persona is None:
        return RedirectResponse(url="/login")
    cuenta = mailbox_account_model.get_for_persona(persona)
    candidatos = []
    if cuenta:
        candidatos = [
            {
                "id": entry.documento.id,
                "estado": entry.documento.estado,
                "asunto": entry.correo_asunto,
                "remitente": entry.correo_remitente,
                "fecha_correo": entry.correo_fecha,
            }
            for entry in candidate_document_model.list_with_email()
        ]
    return templates.TemplateResponse(
        request,
        "candidates_list.html",
        {"cuenta": cuenta, "candidatos": candidatos, "active_tab": "facturas"},
    )


@router.get("/facturas/{candidate_id}", response_class=HTMLResponse)
def factura_detail_page(request: Request, candidate_id: int):
    persona = _current_user_or_none(request)
    if persona is None:
        return RedirectResponse(url="/login")
    entry = candidate_document_model.get_with_email(candidate_id)
    if entry is None:
        return RedirectResponse(url="/facturas")
    doc = entry.documento
    candidato = {
        "asunto": entry.correo_asunto,
        "remitente": entry.correo_remitente,
        "fecha_correo": entry.correo_fecha,
        "estado": doc.estado,
        "motivo_clasificacion": doc.motivo_clasificacion,
        "adjunto_url": f"/api/candidate-documents/{doc.id}/attachment",
    }
    return templates.TemplateResponse(
        request, "candidate_detail.html", {"candidato": candidato, "active_tab": "facturas"}
    )


def _placeholder_page(request: Request, active_tab: str, titulo: str):
    persona = _current_user_or_none(request)
    if persona is None:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        request, "placeholder.html", {"active_tab": active_tab, "titulo": titulo}
    )


@router.get("/proveedores", response_class=HTMLResponse)
def proveedores_page(request: Request):
    return _placeholder_page(request, "proveedores", "Proveedores")


@router.get("/conciliacion", response_class=HTMLResponse)
def conciliacion_page(request: Request):
    return _placeholder_page(request, "conciliacion", "Conciliación")


@router.get("/actividad", response_class=HTMLResponse)
def actividad_page(request: Request):
    return _placeholder_page(request, "actividad", "Actividad")
