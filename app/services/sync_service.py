"""Orquesta una sincronización manual (User Story 2): FR-004 a FR-009, FR-012.

Nunca escribe un estado PROCESADA (Principio II, FR-011): la única salida de esta feature son
candidatos clasificados en REVISIÓN MANUAL, NO ES FACTURA, FACTURA DE VENTA o DUPLICADO IGNORADO.
"""

import logging
from datetime import UTC, datetime

from app.models import candidate_document as candidate_document_model
from app.models import ingested_email as ingested_email_model
from app.models import mailbox_account as mailbox_account_model
from app.models import sync_run as sync_run_model
from app.models.mailbox_account import MailboxAccount
from app.models.sync_run import SyncRun
from app.services import attachment_store, classification, secret_store
from app.services.mailbox.base import MailboxConnectionError
from app.services.mailbox_account_service import build_connector

logger = logging.getLogger("invoice_manager")


class SincronizacionEnCursoError(Exception):
    pass


class CuentaNoDisponibleError(Exception):
    pass


def start_sync(cuenta_id: int, persona_autorizada: str) -> SyncRun:
    account = mailbox_account_model.get_by_id(cuenta_id)
    if account is None or account.persona_autorizada != persona_autorizada:
        raise CuentaNoDisponibleError("Cuenta no encontrada")
    if account.estado != "conectada":
        raise CuentaNoDisponibleError(f"La cuenta no está conectada (estado: {account.estado})")
    if sync_run_model.get_en_curso(cuenta_id) is not None:
        raise SincronizacionEnCursoError("Ya hay una sincronización en curso para esta cuenta")

    sync_run = sync_run_model.create(cuenta_id=cuenta_id, iniciada_por=persona_autorizada)
    _run_sync(account, sync_run)
    return sync_run_model.get_by_id(sync_run.id)


def _run_sync(account: MailboxAccount, sync_run: SyncRun) -> None:
    credenciales = secret_store.retrieve(account.credenciales_ref)
    connector = build_connector(account.proveedor, credenciales)

    since = (
        datetime.fromisoformat(account.ultima_sincronizacion_cursor)
        if account.ultima_sincronizacion_cursor
        else None
    )

    try:
        messages = connector.list_new_messages(since)
    except MailboxConnectionError as exc:
        logger.warning("Sincronización %s interrumpida al listar mensajes: %s", sync_run.id, exc)
        sync_run_model.finish(sync_run.id, "interrumpida")
        return

    try:
        for message in messages:
            _process_message(account, sync_run, connector, message)
            sync_run_model.increment_counters(sync_run.id, correos_procesados=1)
    except MailboxConnectionError as exc:
        logger.warning("Sincronización %s interrumpida a mitad de proceso: %s", sync_run.id, exc)
        sync_run_model.finish(sync_run.id, "interrumpida")
        return

    mailbox_account_model.update_cursor(account.id, datetime.now(UTC).isoformat())
    sync_run_model.finish(sync_run.id, "completada")


def _process_message(account: MailboxAccount, sync_run: SyncRun, connector, message) -> None:
    # FR-009: un mensaje ya ingerido (mismo cuenta_id + message_id) no genera ni fila ni
    # candidato nuevo — se reconoce como duplicado y se salta silenciosamente.
    if ingested_email_model.find_existing(account.id, message.message_id) is not None:
        return

    ingested = ingested_email_model.create(
        cuenta_id=account.id,
        proveedor_message_id=message.message_id,
        remitente=message.remitente,
        asunto=message.asunto,
        fecha_correo=message.fecha.isoformat(),
        primera_sincronizacion_id=sync_run.id,
    )

    for attachment in message.attachments:
        formato = classification.is_supported_format(attachment.content_type)
        if formato is None:
            continue  # FR-005: solo PDF/JPG/PNG se consideran candidatos

        content = attachment.content
        if not content:
            content = connector.get_attachment(message.message_id, attachment.attachment_id).content

        archivo_ref = attachment_store.save_attachment(
            cuenta_id=account.id,
            message_id=message.message_id,
            attachment_id=attachment.attachment_id,
            content=content,
            formato=formato,
        )
        texto_extraido = classification.extract_text(content, formato)
        resultado = classification.classify(message.remitente, message.asunto, texto_extraido)

        candidate_document_model.create(
            correo_id=ingested.id,
            archivo_adjunto_ref=archivo_ref,
            nombre_archivo_original=attachment.filename,
            formato=formato,
            estado=resultado.estado,
            motivo_clasificacion=resultado.motivo,
            sugerido_proveedor_nombre=resultado.sugerido_proveedor_nombre,
            sugerido_fecha_factura=resultado.sugerido_fecha_factura,
            sugerido_numero_factura=resultado.sugerido_numero_factura,
            sugerido_total=resultado.sugerido_total,
        )
        sync_run_model.increment_counters(sync_run.id, candidatos_generados=1)
