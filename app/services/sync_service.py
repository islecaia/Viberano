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
from app.services import attachment_store, classification, secret_store, sync_progress
from app.services.mailbox_account_service import build_connector

logger = logging.getLogger("invoice_manager")


class SincronizacionEnCursoError(Exception):
    pass


class CuentaNoDisponibleError(Exception):
    pass


class LoteNoEncontradoError(Exception):
    """El lote no existe, o no pertenece a la cuenta de la persona autorizada (404)."""


def analizar_lote(cuenta_id: int, persona_autorizada: str) -> SyncRun | None:
    """FR-001 a FR-003, FR-005: lee el buzón y calcula en memoria qué correos nuevos hay y
    cuáles tienen adjuntos candidatos, sin escribir nada en la base de datos todavía. Solo si
    hay al menos un correo con adjunto candidato se crea el lote `pendiente_aprobacion` y se
    persiste (correos + adjuntos); si el resultado es 0 correos con adjunto candidato (lo que
    incluye el caso de 0 correos nuevos), no se crea ningún registro de lote y la cuenta queda
    libre de inmediato para una nueva sincronización (no hay nada `pendiente_aprobacion`/
    `en_curso` que la bloquee) — devuelve `None` en ese caso."""
    account = mailbox_account_model.get_by_id(cuenta_id)
    if account is None or account.persona_autorizada != persona_autorizada:
        raise CuentaNoDisponibleError("Cuenta no encontrada")
    if account.estado != "conectada":
        raise CuentaNoDisponibleError(f"La cuenta no está conectada (estado: {account.estado})")
    if sync_run_model.get_pendiente_o_en_curso(cuenta_id) is not None:
        raise SincronizacionEnCursoError(
            "Ya hay un lote pendiente de aprobación o en ejecución para esta cuenta"
        )

    try:
        sync_progress.set_mensaje(cuenta_id, "Conectando con el buzón…")
        credenciales = secret_store.retrieve(account.credenciales_ref)
        connector = build_connector(account.proveedor, credenciales)
        since = (
            datetime.fromisoformat(account.ultima_sincronizacion_cursor)
            if account.ultima_sincronizacion_cursor
            else None
        )

        sync_progress.set_mensaje(cuenta_id, "Leyendo correos nuevos…")
        messages = connector.list_new_messages(since)
        analizados = _analizar_mensajes(account.id, connector, messages)
        correos_con_adjuntos = sum(1 for correo in analizados if correo["adjuntos"])

        # El buzón ya se leyó hasta aquí independientemente de si hay algo que revisar — avanzar
        # el cursor evita reanalizar los mismos correos sin adjunto en la siguiente sincronización.
        mailbox_account_model.update_cursor(account.id, datetime.now(UTC).isoformat())

        if correos_con_adjuntos == 0:
            return None

        sync_progress.set_mensaje(cuenta_id, "Guardando resultados…")
        sync_run = sync_run_model.create_analisis(
            cuenta_id=cuenta_id, iniciada_por=persona_autorizada
        )
        try:
            _persistir_correos_analizados(sync_run.id, account.id, analizados)
            sync_run_model.guardar_resumen(sync_run.id, len(analizados), correos_con_adjuntos)
        except Exception:
            logger.exception(
                "Análisis del lote %s interrumpido al guardar los datos", sync_run.id
            )
            sync_run_model.marcar_interrumpida(sync_run.id)
            raise
        return sync_run_model.get_by_id(sync_run.id)
    finally:
        sync_progress.clear(cuenta_id)


def _analizar_mensajes(cuenta_id: int, connector, messages) -> list[dict]:
    """Solo lectura y cálculo en memoria (research.md): nada se escribe en la base de datos ni
    en `attachment_store` todavía, para poder descartar el lote entero sin dejar rastro si
    resulta que no tiene ningún adjunto candidato."""
    analizados = []
    total = len(messages)
    for indice, message in enumerate(messages, start=1):
        sync_progress.set_mensaje(cuenta_id, f"Analizando adjuntos… ({indice}/{total})")
        # FR-009 (feature 001): un correo ya ingerido no se vuelve a analizar.
        if ingested_email_model.find_existing(cuenta_id, message.message_id) is not None:
            continue

        adjuntos = []
        for attachment in message.attachments:
            formato = classification.is_supported_format(attachment.content_type)
            if formato is None:
                continue  # FR-005 (feature 001): solo PDF/JPG/PNG son candidatos

            content = attachment.content
            if not content:
                content = connector.get_attachment(
                    message.message_id, attachment.attachment_id
                ).content
            adjuntos.append(
                {
                    "attachment_id": attachment.attachment_id,
                    "filename": attachment.filename,
                    "formato": formato,
                    "content": content,
                }
            )

        analizados.append({"message": message, "adjuntos": adjuntos})
    return analizados


def _persistir_correos_analizados(sync_run_id: int, cuenta_id: int, analizados: list[dict]) -> None:
    for correo in analizados:
        message = correo["message"]
        ingested = ingested_email_model.create(
            cuenta_id=cuenta_id,
            proveedor_message_id=message.message_id,
            remitente=message.remitente,
            asunto=message.asunto,
            fecha_correo=message.fecha.isoformat(),
            primera_sincronizacion_id=sync_run_id,
        )
        for adjunto in correo["adjuntos"]:
            archivo_ref = attachment_store.save_attachment(
                cuenta_id=cuenta_id,
                message_id=message.message_id,
                attachment_id=adjunto["attachment_id"],
                content=adjunto["content"],
                formato=adjunto["formato"],
            )
            pending_attachment_model.create(
                correo_id=ingested.id,
                archivo_adjunto_ref=archivo_ref,
                nombre_archivo_original=adjunto["filename"],
                formato=adjunto["formato"],
            )


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
        # Nada que procesar: puede ser un reintento repetido sobre un lote ya `completada` (dos
        # clics, dos pestañas), o un lote que nunca llegó a tener ningún correo (dato heredado de
        # antes de FR-013, o una condición de carrera). En ambos casos se cierra sin error en vez
        # de dejarlo atascado sin ninguna acción posible desde la UI (bug real observado: un lote
        # `pendiente_aprobacion` con 0/0 solo podía desbloquearse editando la base de datos).
        if sync_run.estado != "completada":
            sync_run_model.marcar_completada(sync_run_id)
        return sync_run_model.get_by_id(sync_run_id)

    sync_run_model.marcar_en_curso(sync_run_id)
    total = len(correos)
    try:
        try:
            for indice, correo in enumerate(correos, start=1):
                sync_progress.set_mensaje(
                    account.id, f"Clasificando con IA… ({indice}/{total} correos)"
                )
                try:
                    _procesar_correo_pendiente(sync_run_id, correo)
                except Exception as exc:  # noqa: BLE001 - FR-009: un correo no bloquea el resto
                    logger.warning(
                        "Correo %s del lote %s falló al procesarse: %s",
                        correo.id,
                        sync_run_id,
                        exc,
                    )
                    ingested_email_model.marcar_fallido(correo.id, str(exc))
                sync_run_model.increment_counters(sync_run_id, correos_procesados=1)
            sync_progress.set_mensaje(account.id, "Finalizando…")
        except Exception:
            logger.exception(
                "Ejecución del lote %s interrumpida por un error inesperado", sync_run_id
            )
            sync_run_model.marcar_interrumpida(sync_run_id)
            raise
    finally:
        sync_progress.clear(account.id)

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
