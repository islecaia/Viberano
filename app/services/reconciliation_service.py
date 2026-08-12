"""Orquesta una conciliación bancaria manual (User Story 1): FR-001 a FR-005, FR-011, FR-012.

Nunca marca una factura como impagada (Principio VI): solo CONCILIADA, NO ENCONTRADA EN EXTRACTO
o PENDIENTE REVISIÓN CONCILIACIÓN. La conciliación solo se ejecuta cuando se llama a
`procesar_extracto` explícitamente (Principio V) — nada la dispara automáticamente.
"""

import csv
import io
from datetime import date

from app.models import bank_movement as bank_movement_model
from app.models import bank_statement as bank_statement_model
from app.models import candidate_document as candidate_document_model
from app.models import reconciliation_candidate as reconciliation_candidate_model

_COLUMNAS_REQUERIDAS = {"fecha", "importe", "concepto"}
_VENTANA_DIAS = 10


class ExtractoInvalidoError(Exception):
    """El CSV no tiene las columnas requeridas o alguna fila no es parseable (FR-011)."""


def _parsear_csv(contenido: bytes) -> list[dict]:
    """Valida el CSV completo antes de devolver nada — todo o nada (FR-011)."""
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ExtractoInvalidoError("El archivo no es un CSV de texto válido (UTF-8)") from exc

    lector = csv.DictReader(io.StringIO(texto))
    if not lector.fieldnames:
        raise ExtractoInvalidoError("El CSV está vacío")
    cabecera = {c.strip().lower() for c in lector.fieldnames}
    if not _COLUMNAS_REQUERIDAS.issubset(cabecera):
        faltantes = _COLUMNAS_REQUERIDAS - cabecera
        raise ExtractoInvalidoError(f"Faltan columnas en el CSV: {', '.join(sorted(faltantes))}")

    filas_normalizadas = []
    for fila in lector:
        fila_norm = {(k or "").strip().lower(): v for k, v in fila.items()}
        fecha_raw = (fila_norm.get("fecha") or "").strip()
        concepto = (fila_norm.get("concepto") or "").strip()
        try:
            date.fromisoformat(fecha_raw)
            importe = float(fila_norm.get("importe"))
        except (TypeError, ValueError) as exc:
            raise ExtractoInvalidoError(f"Fila con datos inválidos: {fila}") from exc
        filas_normalizadas.append({"fecha": fecha_raw, "importe": importe, "concepto": concepto})

    if not filas_normalizadas:
        raise ExtractoInvalidoError("El CSV no contiene ningún movimiento")
    return filas_normalizadas


def procesar_extracto(contenido: bytes, aportado_por: str) -> dict:
    """FR-001 a FR-005: aporta el extracto y ejecuta la conciliación sobre las facturas
    PROCESADA del periodo (FR-012) que todavía no se hayan evaluado (research.md §4)."""
    movimientos_datos = _parsear_csv(contenido)

    fechas = [m["fecha"] for m in movimientos_datos]
    fecha_inicio, fecha_fin = min(fechas), max(fechas)

    extracto = bank_statement_model.create(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        aportado_por=aportado_por,
        total_movimientos=len(movimientos_datos),
    )
    bank_movement_model.create_bulk(extracto.id, movimientos_datos)

    conciliadas = no_encontradas = pendientes = 0
    facturas = candidate_document_model.list_procesada_sin_conciliar(fecha_inicio, fecha_fin)
    for factura in facturas:
        candidatos = bank_movement_model.find_candidatos(
            extracto.id, factura.total, factura.fecha_factura, _VENTANA_DIAS
        )
        if len(candidatos) == 1:
            candidate_document_model.mark_conciliada(factura.id, candidatos[0].id, extracto.id)
            conciliadas += 1
        elif len(candidatos) == 0:
            candidate_document_model.mark_no_encontrada(factura.id, extracto.id)
            no_encontradas += 1
        else:
            candidate_document_model.mark_pendiente_revision(factura.id, extracto.id)
            reconciliation_candidate_model.create_many(factura.id, [c.id for c in candidatos])
            pendientes += 1

    return {
        "extracto": extracto,
        "conciliadas": conciliadas,
        "no_encontradas": no_encontradas,
        "pendientes_revision": pendientes,
    }
