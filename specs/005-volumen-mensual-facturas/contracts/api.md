# API Contract: Volumen Mensual de Facturas

**Fase**: 1 — Design & Contracts
**Spec**: [spec.md](../spec.md) · **Data model**: [data-model.md](../data-model.md)

Requiere sesión de persona autorizada activa (heredado de las features anteriores). Es una
consulta de solo lectura (FR-009): ningún endpoint de este contrato escribe ni cambia el estado
de ninguna factura.

## GET /api/metrics/volumen-mensual

Consulta el recuento de facturas `PROCESADA` por mes y la media del periodo (User Stories 1 y 2).

**Query params** (ambos opcionales):

| Param | Formato | Notas |
|---|---|---|
| `desde` | `YYYY-MM` | Primer mes del periodo (inclusive). Por defecto: 11 meses antes del mes en curso (research.md §3). |
| `hasta` | `YYYY-MM` | Último mes del periodo (inclusive). Por defecto: mes en curso. |

**Response `200 OK`**:

```json
{
  "desde": "2025-09",
  "hasta": "2026-08",
  "meses": [
    { "mes": "2025-09", "total": 12, "completo": true },
    { "mes": "2025-10", "total": 9, "completo": true },
    { "mes": "2026-08", "total": 3, "completo": false }
  ],
  "media_meses_completos": 10.5,
  "media_con_mes_parcial": 9.8
}
```

- `meses` incluye **todos** los meses del rango `desde`..`hasta`, uno por uno, incluidos los que
  tienen `total: 0` (FR-005) — nunca se omite un mes.
- `completo: false` marca el mes en curso y, si aplica, el primer mes de conexión de la cuenta
  (research.md §2).
- `media_meses_completos` es `null` si ningún mes del periodo tiene `completo: true`.
- `media_con_mes_parcial` es `null` solo si el periodo no tiene ningún mes (caso imposible con
  `desde`/`hasta` válidos, ya que el rango incluye como mínimo un mes).

**Errores**:
- `422 Unprocessable Entity`: `desde` o `hasta` no tienen formato `YYYY-MM`, o `desde` es
  posterior a `hasta`.

---

## Sin cambios

Ningún endpoint de las features 001-004 cambia su comportamiento. Esta feature no toca la
ingesta, la validación/archivado, el catálogo de proveedores ni la conciliación bancaria.
