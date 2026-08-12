"""Páginas HTML server-rendered (fuera de /api/): no exigen sesión vía 401 JSON, sino redirect."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.session import verify_session_token
from app.models import bank_movement as bank_movement_model
from app.models import bank_statement as bank_statement_model
from app.models import candidate_document as candidate_document_model
from app.models import mailbox_account as mailbox_account_model
from app.models import provider as provider_model
from app.models import reconciliation_candidate as reconciliation_candidate_model

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
    proveedor = provider_model.get_by_id(doc.proveedor_id) if doc.proveedor_id else None
    candidato = {
        "id": doc.id,
        "asunto": entry.correo_asunto,
        "remitente": entry.correo_remitente,
        "fecha_correo": entry.correo_fecha,
        "estado": doc.estado,
        "motivo_clasificacion": doc.motivo_clasificacion,
        "adjunto_url": f"/api/candidate-documents/{doc.id}/attachment",
        "proveedor_nombre": proveedor.nombre if proveedor else None,
        "fecha_factura": doc.fecha_factura,
        "numero_factura": doc.numero_factura,
        "total": doc.total,
        "es_nota_credito": doc.es_nota_credito,
        "validado_por": doc.validado_por,
        "fecha_validacion": doc.fecha_validacion,
        "sugerido_proveedor_nombre": None,
        "sugerido_proveedor_id_coincidente": None,
        "sugerido_fecha_factura": None,
        "sugerido_numero_factura": None,
        "sugerido_total": None,
        "estado_conciliacion": doc.estado_conciliacion,
        "movimiento_conciliado": None,
        "conciliacion_candidatos": [],
    }
    if doc.estado_conciliacion == "CONCILIADA" and doc.movimiento_bancario_id:
        movimiento = bank_movement_model.get_by_id(doc.movimiento_bancario_id)
        if movimiento is not None:
            candidato["movimiento_conciliado"] = {
                "fecha": movimiento.fecha,
                "importe": movimiento.importe,
                "concepto": movimiento.concepto,
            }
    elif doc.estado_conciliacion == "PENDIENTE REVISIÓN CONCILIACIÓN":
        candidatos = reconciliation_candidate_model.list_for_documento(doc.id)
        movimientos = [bank_movement_model.get_by_id(c.movimiento_id) for c in candidatos]
        candidato["conciliacion_candidatos"] = [
            {"id": m.id, "fecha": m.fecha, "importe": m.importe, "concepto": m.concepto}
            for m in movimientos
            if m is not None
        ]
    # FR-008 de specs/003-sugerencia-datos-factura/: solo se muestra sugerencia en REVISIÓN MANUAL.
    if doc.estado == candidate_document_model.ESTADO_REVISION_MANUAL:
        proveedor_coincidente = None
        if doc.sugerido_proveedor_nombre:
            coincidencia = provider_model.get_by_nombre_normalizado(doc.sugerido_proveedor_nombre)
            proveedor_coincidente = coincidencia.id if coincidencia else None
        candidato.update(
            {
                "sugerido_proveedor_nombre": doc.sugerido_proveedor_nombre,
                "sugerido_proveedor_id_coincidente": proveedor_coincidente,
                "sugerido_fecha_factura": doc.sugerido_fecha_factura,
                "sugerido_numero_factura": doc.sugerido_numero_factura,
                "sugerido_total": doc.sugerido_total,
            }
        )
    proveedores_activos = provider_model.list_all(activo=True)
    return templates.TemplateResponse(
        request,
        "candidate_detail.html",
        {
            "candidato": candidato,
            "proveedores_activos": proveedores_activos,
            "active_tab": "facturas",
        },
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
    persona = _current_user_or_none(request)
    if persona is None:
        return RedirectResponse(url="/login")
    proveedores = provider_model.list_all()
    return templates.TemplateResponse(
        request, "providers.html", {"proveedores": proveedores, "active_tab": "proveedores"}
    )


@router.get("/conciliacion", response_class=HTMLResponse)
def conciliacion_page(request: Request):
    persona = _current_user_or_none(request)
    if persona is None:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        request, "reconciliation.html", {"active_tab": "conciliacion", "detalle": None}
    )


@router.get("/conciliacion/{reconciliation_id}", response_class=HTMLResponse)
def conciliacion_detail_page(request: Request, reconciliation_id: int):
    persona = _current_user_or_none(request)
    if persona is None:
        return RedirectResponse(url="/login")
    statement = bank_statement_model.get_by_id(reconciliation_id)
    if statement is None:
        return RedirectResponse(url="/conciliacion")
    detalle = {
        "id": statement.id,
        "fecha_inicio": statement.fecha_inicio,
        "fecha_fin": statement.fecha_fin,
        "total_movimientos": statement.total_movimientos,
        "conciliadas": candidate_document_model.list_by_extracto(reconciliation_id, "CONCILIADA"),
        "no_encontradas": candidate_document_model.list_by_extracto(
            reconciliation_id, "NO ENCONTRADA EN EXTRACTO"
        ),
        "pendientes": candidate_document_model.list_by_extracto(
            reconciliation_id, "PENDIENTE REVISIÓN CONCILIACIÓN"
        ),
        "pendientes_de_justificar": bank_movement_model.find_pendientes_de_justificar(
            reconciliation_id
        ),
    }
    return templates.TemplateResponse(
        request, "reconciliation.html", {"active_tab": "conciliacion", "detalle": detalle}
    )


@router.get("/actividad", response_class=HTMLResponse)
def actividad_page(request: Request):
    return _placeholder_page(request, "actividad", "Actividad")
