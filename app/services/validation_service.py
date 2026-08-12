"""Valida los cuatro campos y confirma el archivado (User Story 1: FR-001 a FR-004, FR-008).

Traduce los datos de entrada a errores específicos para que la capa de rutas los convierta en
el código HTTP correcto (contracts/api.md de specs/002-validacion-archivado-facturas/).
"""

from datetime import date

from app.models import candidate_document as candidate_document_model
from app.models import provider as provider_model


class CampoInvalidoError(Exception):
    """Falta un campo obligatorio o su valor no es válido (422)."""


class ProveedorInactivoError(Exception):
    """El proveedor indicado existe pero no está activo (409); incluye su id (FR-002/FR-003)."""

    def __init__(self, proveedor_id: int):
        self.proveedor_id = proveedor_id
        super().__init__(f"El proveedor {proveedor_id} no está activo")


def _validar_fecha(fecha_factura: str) -> None:
    try:
        date.fromisoformat(fecha_factura)
    except (TypeError, ValueError) as exc:
        raise CampoInvalidoError("fecha_factura no es una fecha válida (YYYY-MM-DD)") from exc


def _resolver_proveedor(
    proveedor_id: int | None,
    proveedor_nombre_nuevo: str | None,
    proveedor_nif_nuevo: str | None = None,
) -> provider_model.Provider:
    if proveedor_id is not None:
        proveedor = provider_model.get_by_id(proveedor_id)
        if proveedor is None:
            raise CampoInvalidoError(f"El proveedor {proveedor_id} no existe")
        return proveedor
    if proveedor_nombre_nuevo and proveedor_nombre_nuevo.strip():
        existente = provider_model.get_by_nombre_normalizado(proveedor_nombre_nuevo)
        if existente is not None:
            return existente
        nif = proveedor_nif_nuevo.strip() if proveedor_nif_nuevo else None
        return provider_model.create(proveedor_nombre_nuevo.strip(), nif or None)
    raise CampoInvalidoError("Debe indicarse proveedor_id o proveedor_nombre_nuevo")


def validate_and_archive(
    candidate_id: int,
    fecha_factura: str,
    numero_factura: str,
    total: float,
    es_nota_credito: bool,
    validado_por: str,
    proveedor_id: int | None = None,
    proveedor_nombre_nuevo: str | None = None,
    proveedor_nif_nuevo: str | None = None,
) -> candidate_document_model.CandidateDocument:
    if not fecha_factura:
        raise CampoInvalidoError("fecha_factura es obligatoria")
    _validar_fecha(fecha_factura)

    if not numero_factura or not numero_factura.strip():
        raise CampoInvalidoError("numero_factura es obligatorio")
    numero_factura = numero_factura.strip()

    if not isinstance(total, int | float):
        raise CampoInvalidoError("total debe ser numérico")
    if total == 0:
        raise CampoInvalidoError(
            "total no puede ser cero (spec.md raíz FR-010: superior a cero para archivo automático)"
        )
    if total < 0 and not es_nota_credito:
        raise CampoInvalidoError(
            "total negativo solo es válido si es_nota_credito es true (edge case de spec.md)"
        )

    proveedor = _resolver_proveedor(proveedor_id, proveedor_nombre_nuevo, proveedor_nif_nuevo)
    if not proveedor.activo:
        raise ProveedorInactivoError(proveedor.id)

    duplicado = candidate_document_model.find_procesada_duplicado(
        proveedor.id, fecha_factura, numero_factura
    )
    if duplicado is not None:
        raise candidate_document_model.ArchivadoDuplicadoError(duplicado.id)

    return candidate_document_model.mark_procesada(
        candidate_id=candidate_id,
        proveedor_id=proveedor.id,
        fecha_factura=fecha_factura,
        numero_factura=numero_factura,
        total=float(total),
        es_nota_credito=es_nota_credito,
        validado_por=validado_por,
    )
