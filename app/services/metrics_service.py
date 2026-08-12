"""Agregación de solo lectura para specs/005-volumen-mensual-facturas/ (FR-001 a FR-009).

No persiste nada: el recuento y la media se recalculan en cada consulta a partir de
`candidate_documents` ya existente (data-model.md).
"""

import re
from calendar import monthrange
from datetime import date

from app.models import candidate_document as candidate_document_model

_FORMATO_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class PeriodoInvalidoError(ValueError):
    """`desde`/`hasta` no tienen formato `YYYY-MM`, o `desde` es posterior a `hasta`
    (contracts/api.md)."""


def _mes_actual() -> str:
    return date.today().strftime("%Y-%m")


def _restar_meses(mes: str, cantidad: int) -> str:
    anio, num_mes = (int(parte) for parte in mes.split("-"))
    total = anio * 12 + (num_mes - 1) - cantidad
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def resolver_periodo(desde: str | None, hasta: str | None) -> tuple[str, str]:
    """Por defecto: los últimos 12 meses rodantes (research.md §3, spec.md Assumptions). Lanza
    `PeriodoInvalidoError` si el formato no es `YYYY-MM` o si `desde` es posterior a `hasta`."""
    hoy = _mes_actual()
    desde_final = desde or _restar_meses(hoy, 11)
    hasta_final = hasta or hoy
    for valor in (desde_final, hasta_final):
        if not _FORMATO_MES.match(valor):
            raise PeriodoInvalidoError(f"Formato de mes inválido: {valor!r} (se espera YYYY-MM)")
    if desde_final > hasta_final:
        raise PeriodoInvalidoError("'desde' no puede ser posterior a 'hasta'")
    return desde_final, hasta_final


def _primer_dia(mes: str) -> str:
    return f"{mes}-01"


def _ultimo_dia(mes: str) -> str:
    anio, num_mes = (int(parte) for parte in mes.split("-"))
    return f"{mes}-{monthrange(anio, num_mes)[1]:02d}"


def _rango_meses(desde: str, hasta: str) -> list[str]:
    """Todos los años-mes entre `desde` y `hasta` (`YYYY-MM`), ambos inclusive."""
    anio, mes = (int(parte) for parte in desde.split("-"))
    fin_anio, fin_mes = (int(parte) for parte in hasta.split("-"))
    meses = []
    while (anio, mes) <= (fin_anio, fin_mes):
        meses.append(f"{anio:04d}-{mes:02d}")
        mes += 1
        if mes > 12:
            mes = 1
            anio += 1
    return meses


def _es_mes_parcial(mes: str, fecha_conexion_cuenta: str | None) -> bool:
    """FR-007/FR-008, research.md §2: el mes en curso siempre es parcial; el mes de conexión de
    la cuenta también lo es si la conexión ocurrió después del día 1 de ese mes."""
    if mes == _mes_actual():
        return True
    if fecha_conexion_cuenta:
        mes_conexion = fecha_conexion_cuenta[:7]
        dia_conexion = int(fecha_conexion_cuenta[8:10])
        if mes == mes_conexion and dia_conexion > 1:
            return True
    return False


def _media(totales: list[int]) -> float | None:
    return sum(totales) / len(totales) if totales else None


def volumen_mensual(desde: str, hasta: str, fecha_conexion_cuenta: str | None = None) -> dict:
    """FR-001 a FR-008: recuento de facturas PROCESADA por mes del periodo `[desde, hasta]`
    (`YYYY-MM`), incluyendo los meses sin ninguna factura con `total: 0` (nunca se omiten), más
    la media de meses completos y la media que incluye el mes parcial (data-model.md § Media del
    Periodo)."""
    recuentos = {
        fila["mes"]: fila["total"]
        for fila in candidate_document_model.count_procesada_por_mes(
            _primer_dia(desde), _ultimo_dia(hasta)
        )
    }
    meses = [
        {
            "mes": mes,
            "total": recuentos.get(mes, 0),
            "completo": not _es_mes_parcial(mes, fecha_conexion_cuenta),
        }
        for mes in _rango_meses(desde, hasta)
    ]
    return {
        "desde": desde,
        "hasta": hasta,
        "meses": meses,
        "media_meses_completos": _media([m["total"] for m in meses if m["completo"]]),
        "media_con_mes_parcial": _media([m["total"] for m in meses]),
    }
