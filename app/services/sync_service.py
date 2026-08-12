"""Orquesta la sincronización en dos fases explícitas (specs/006-lotes-aprobacion-previa/):
`analizar_lote()` lee el buzón, guarda cada correo nuevo y sus adjuntos candidatos sin
clasificarlos (FR-001 a FR-003); `ejecutar_lote()` clasifica y crea los documentos candidato,
solo tras aprobación explícita de la persona autorizada, y sirve indistintamente para aprobar,
reanudar tras una interrupción, o reintentar los correos fallidos (research.md §5).

Nunca escribe un estado PROCESADA (Principio II, FR-011 de la feature 001): la única salida de
esta feature son candidatos clasificados en REVISIÓN MANUAL, NO ES FACTURA, FACTURA DE VENTA o
DUPLICADO IGNORADO.
"""

import logging
from datetime import UTC, datetime

from app.models import candidate_document as candidate_document_model
from app.models import ingested_email as ingested_email_model
from app.models import mailbox_account as mailbox_account_model
from app.models import pending_attachment as pending_attachment_model
from app.models import sync_run as sync_run_model
from app.models.ingested_email import IngestedEmail
from app.models.sync_run import SyncRun
from app.services import attachment_store, classification, secret_store
from app.services.mailbox.base import MailboxConnectionError
from app.services.mailbox_account_service import build_connector

logger = logging.getLogger("invoice_manager")


class SincronizacionEnCursoError(Exception):
    pass


class CuentaNoDisponibleError(Exception):
    pass


class LoteNoEncontradoError(Exception):
    """El lote no existe, o no pertenece a la cuenta de la persona autorizada (404)."""


class NadaQueEjecutarError(Exception):
    """El lote no tiene ningún correo `PENDIENTE`/`FALLIDO` que procesar (422)."""


def analizar_lote(cuenta_id: int, persona_autorizada: str) -> SyncRun:
    """FR-001 a FR-003, FR-005: lee el buzón, guarda cada correo nuevo y sus adjuntos candidatos
    sin clasificarlos ni crear ningún `candidate_document`, y deja el lote `pendiente_aprobacion`
    con su resumen (correos nuevos, correos con adjuntos candidatos)."""
    account = mailbox_account_model.get_by_id(cuenta_id)
    if account is None or account.persona_autorizada != persona_autorizada:
        raise CuentaNoDisponibleError("Cuenta no encontrada")
    if account.estado != "conectada":
        raise CuentaNoDisponibleError(f"La cuenta no está conectada (estado: {account.estado})")
    if sync_run_model.get_pendiente_o_en_curso(cuenta_id) is not None:
        raise SincronizacionEnCursoError(
            "Ya hay un lote pendiente de aprobación o en ejecución para esta cuenta"
        )

    sync_run = sync_run_model.create_analisis(
        cuenta_id=cuenta_id, iniciada_por=persona_autorizada
    )

    try:
        credenciales = secret_store.retrieve(account.credenciales_ref)
        connector = build_connector(account.proveedor, credenciales)

        since = (
            datetime.fromisoformat(account.ultima_sincronizacion_cursor)
            if account.ultima_sincronizacion_cursor
            else None
        )

        messages = connector.list_new_messages(since)
        correos_nuevos, correos_con_adjuntos = _guardar_correos_nuevos(
            account.id, sync_run.id, connector, messages
        )
    except MailboxConnectionError as exc:
        logger.warning("Análisis del lote %s interrumpido: %s", sync_run.id, exc)
        sync_run_model.marcar_interrumpida(sync_run.id)
        return sync_run_model.get_by_id(sync_run.id)
    except Exception:
        logger.exception(
            "Análisis del lote %s interrumpido por un error inesperado", sync_run.id
        )
        sync_run_model.marcar_interrumpida(sync_run.id)
        raise

    mailbox_account_model.update_cursor(account.id, datetime.now(UTC).isoformat())
    sync_run_model.guardar_resumen(sync_run.id, correos_nuevos, correos_con_adjuntos)
    return sync_run_model.get_by_id(sync_run.id)


def _guardar_correos_nuevos(
    cuenta_id: int, sync_run_id: int, connector, messages
) -> tuple[int, int]:
    correos_nuevos = 0
    correos_con_adjuntos = 0
    for message in messages:
        # FR-009 (feature 001): un correo ya ingerido no genera ni fila ni adjunto nuevo.
        if ingested_email_model.find_existing(cuenta_id, message.message_id) is not None:
            continue

        correos_nuevos += 1
        ingested = ingested_email_model.create(
            cuenta_id=cuenta_id,
            proveedor_message_id=message.message_id,
            remitente=message.remitente,
            asunto=message.asunto,
            fecha_correo=message.fecha.isoformat(),
            primera_sincronizacion_id=sync_run_id,
        )

        tiene_adjunto_candidato = False
        for attachment in message.attachments:
            formato = classification.is_supported_format(attachment.content_type)
            if formato is None:
                continue  # FR-005 (feature 001): solo PDF/JPG/PNG son candidatos

            tiene_adjunto_candidato = True
            content = attachment.content
            if not content:
                content = connector.get_attachment(
                    message.message_id, attachment.attachment_id
                ).content

            archivo_ref = attachment_store.save_attachment(
                cuenta_id=cuenta_id,
                message_id=message.message_id,
                attachment_id=attachment.attachment_id,
                content=content,
                formato=formato,
            )
            pending_attachment_model.create(
                correo_id=ingested.id,
                archivo_adjunto_ref=archivo_ref,
                nombre_archivo_original=attachment.filename,
                formato=formato,
            )

        if tiene_adjunto_candidato:
            correos_con_adjuntos += 1
    return correos_nuevos, correos_con_adjuntos


def ejecutar_lote(sync_run_id: int, persona_autorizada: str) -> SyncRun:
    """FR-004, FR-006 a FR-011: clasifica y crea los documentos candidato de los correos
    `PENDIENTE`/`FALLIDO` de este lote. Un fallo al procesar un correo concreto no bloquea el
    resto (FR-009) — se aísla con su propio try/except; el `except` amplio que envuelve todo el
    bucle sigue existiendo como red de seguridad para fallos sistémicos (revisión de código
    anterior), no para fallos de un único correo."""
    sync_run = sync_run_model.get_by_id(sync_run_id)
    if sync_run is None:
        raise LoteNoEncontradoError(f"El lote {sync_run_id} no existe")
    account = mailbox_account_model.get_by_id(sync_run.cuenta_id)
    if account is None or account.persona_autorizada != persona_autorizada:
        raise LoteNoEncontradoError(f"El lote {sync_run_id} no existe")

    correos = ingested_email_model.list_pendientes_o_fallidos(sync_run_id)
    if not correos:
        raise NadaQueEjecutarError(
            f"El lote {sync_run_id} no tiene ningún correo pendiente ni fallido"
        )

    sync_run_model.marcar_en_curso(sync_run_id)
    try:
        for correo in correos:
            try:
                _procesar_correo_pendiente(sync_run_id, correo)
            except Exception as exc:  # noqa: BLE001 - FR-009: un correo no bloquea el resto
                logger.warning(
                    "Correo %s del lote %s falló al procesarse: %s", correo.id, sync_run_id, exc
                )
                ingested_email_model.marcar_fallido(correo.id, str(exc))
            sync_run_model.increment_counters(sync_run_id, correos_procesados=1)
    except Exception:
        logger.exception(
            "Ejecución del lote %s interrumpida por un error inesperado", sync_run_id
        )
        sync_run_model.marcar_interrumpida(sync_run_id)
        raise

    sync_run_model.marcar_completada(sync_run_id)
    return sync_run_model.get_by_id(sync_run_id)


def _procesar_correo_pendiente(sync_run_id: int, correo: IngestedEmail) -> None:
    for adjunto in pending_attachment_model.list_for_correo(correo.id):
        contenido = attachment_store.read_attachment(adjunto.archivo_adjunto_ref)
        texto_extraido = classification.extract_text(contenido, adjunto.formato)
        resultado = classification.classify(correo.remitente, correo.asunto, texto_extraido)

        candidate_document_model.create(
            correo_id=correo.id,
            archivo_adjunto_ref=adjunto.archivo_adjunto_ref,
            nombre_archivo_original=adjunto.nombre_archivo_original,
            formato=adjunto.formato,
            estado=resultado.estado,
            motivo_clasificacion=resultado.motivo,
            sugerido_proveedor_nombre=resultado.sugerido_proveedor_nombre,
            sugerido_fecha_factura=resultado.sugerido_fecha_factura,
            sugerido_numero_factura=resultado.sugerido_numero_factura,
            sugerido_total=resultado.sugerido_total,
        )
        sync_run_model.increment_counters(sync_run_id, candidatos_generados=1)
        # Se borra en cuanto se convierte (no todos juntos al final): si un correo con varios
        # adjuntos falla a mitad, los ya convertidos no se reprocesan ni duplican al reintentar.
        pending_attachment_model.delete(adjunto.id)

    ingested_email_model.marcar_procesado(correo.id)
