"""Filtro de formato y clasificación acotada con Anthropic API (research.md §4).

Principio VII de la constitution: la Anthropic API SOLO clasifica (nunca decide archivado) y su
volumen está acotado a una llamada por adjunto que ya pasó el filtro de formato. Principio I:
ante fallo, timeout o baja confianza, el resultado por defecto es REVISIÓN MANUAL — nunca se
inventa una clasificación certera ni se descarta el documento.
"""

import io
import json
import logging
import os

import anthropic
from pypdf import PdfReader

logger = logging.getLogger("invoice_manager")

SUPPORTED_CONTENT_TYPES = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
}

_CLASSIFICATION_TIMEOUT_SECONDS = 20
_CONFIDENCE_THRESHOLD = 0.6
_MAX_EXTRACTED_CHARS = 4000

REVISION_MANUAL = "REVISIÓN MANUAL"
NO_ES_FACTURA = "NO ES FACTURA"
FACTURA_DE_VENTA = "FACTURA DE VENTA"


def is_supported_format(content_type: str) -> str | None:
    """FR-005: solo PDF/JPG/PNG se consideran candidatos a clasificación."""
    return SUPPORTED_CONTENT_TYPES.get(content_type)


def extract_text(content: bytes, formato: str) -> str:
    """Extrae texto del adjunto para pasarlo a clasificación (research.md §4).

    Para imágenes no se aplica OCR en esta versión (no forma parte del stack declarado en la
    constitution); se clasifica solo con remitente/asunto, lo que empuja los casos ambiguos a
    REVISIÓN MANUAL de forma segura (Principio I) en vez de fallar.
    """
    if formato != "pdf":
        return ""
    try:
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text[:_MAX_EXTRACTED_CHARS]
    except Exception:  # noqa: BLE001 - un PDF corrupto no debe tumbar la sincronización
        logger.warning("No se pudo extraer texto del PDF; se clasificará con menos contexto")
        return ""


def classify(remitente: str, asunto: str, texto_extraido: str) -> tuple[str, str]:
    """Devuelve (estado, motivo). Estado es REVISIÓN MANUAL, NO ES FACTURA o FACTURA DE VENTA.

    Nunca devuelve un estado "positivo" (candidato a gasto) certero: eso lo decide una persona en
    REVISIÓN MANUAL (Principio I y II) — esta función solo distingue lo que puede descartar con
    confianza (no es factura / es factura de venta) de lo que debe revisar un humano.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return REVISION_MANUAL, "Sin ANTHROPIC_API_KEY configurada; requiere revisión manual"

    client = anthropic.Anthropic(api_key=api_key, timeout=_CLASSIFICATION_TIMEOUT_SECONDS)
    model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    opciones = f'"{REVISION_MANUAL}", "{NO_ES_FACTURA}" o "{FACTURA_DE_VENTA}"'
    prompt = (
        f"Clasifica este correo con adjunto como una de estas tres opciones exactas: {opciones}.\n"
        f"- {REVISION_MANUAL}: podría ser una factura de gasto recibida "
        "(dejar que la revise una persona).\n"
        f"- {NO_ES_FACTURA}: el documento claramente no es una factura "
        "(recibo, presupuesto, publicidad...).\n"
        f"- {FACTURA_DE_VENTA}: es una factura emitida por el propio usuario, "
        "no un gasto recibido.\n"
        "Ante cualquier duda, responde REVISIÓN MANUAL.\n\n"
        f"Remitente: {remitente}\nAsunto: {asunto}\n"
        f"Texto extraído del adjunto:\n{texto_extraido}\n\n"
        'Responde solo JSON: {"estado": "...", "confianza": 0.0-1.0, "motivo": "..."}'
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        data = json.loads(raw_text)
        estado = data.get("estado")
        confianza = float(data.get("confianza", 0))
        motivo = data.get("motivo", "")
    except Exception as exc:  # noqa: BLE001 - cualquier fallo cae a REVISIÓN MANUAL
        logger.warning("Fallo en clasificación con Anthropic API: %s", exc)
        return REVISION_MANUAL, "Clasificación no concluyente: fallo o timeout en la llamada de IA"

    estados_validos = {REVISION_MANUAL, NO_ES_FACTURA, FACTURA_DE_VENTA}
    if estado not in estados_validos or confianza < _CONFIDENCE_THRESHOLD:
        return REVISION_MANUAL, motivo or "Confianza de clasificación por debajo del umbral"
    return estado, motivo or f"Clasificado como {estado}"
