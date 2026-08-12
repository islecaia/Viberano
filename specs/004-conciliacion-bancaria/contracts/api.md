# API Contract: Conciliación Bancaria

**Fase**: 1 — Design & Contracts
**Spec**: [spec.md](../spec.md) · **Data model**: [data-model.md](../data-model.md)

Todos los endpoints requieren sesión de persona autorizada activa (heredado de las features
anteriores).

## POST /api/reconciliations

Aporta un extracto y ejecuta la conciliación (User Story 1, FR-001 a FR-005, FR-011).

**Request**: `multipart/form-data` con un campo `extracto` (archivo CSV; cabecera
`fecha,importe,concepto`, research.md §2).

**Response `201 Created`**:
```json
{
  "id": 1,
  "fecha_inicio": "2026-07-01",
  "fecha_fin": "2026-07-31",
  "total_movimientos": 42,
  "conciliadas": 30,
  "no_encontradas": 8,
  "pendientes_revision": 4
}
```

**Errores**: `422` el archivo no es un CSV válido o le faltan columnas obligatorias (FR-011) — no
se crea ningún registro.

---

## GET /api/reconciliations/{id}

Consulta el resultado de una conciliación ya ejecutada.

**Response `200 OK`**:
```json
{
  "id": 1,
  "fecha_inicio": "2026-07-01",
  "fecha_fin": "2026-07-31",
  "aportado_por": "isleca@protonmail.com",
  "fecha_aporte": "2026-08-11T10:00:00Z",
  "total_movimientos": 42,
  "facturas_conciliadas": [ { "documento_id": 501, "movimiento_id": 12 } ],
  "facturas_no_encontradas": [ { "documento_id": 502 } ],
  "facturas_pendientes_revision": [
    { "documento_id": 503, "candidatos": [ { "movimiento_id": 15, "fecha": "2026-07-05", "importe": -120.0, "concepto": "..." } ] }
  ],
  "movimientos_pendientes_de_justificar": [
    { "movimiento_id": 20, "fecha": "2026-07-12", "importe": -45.0, "concepto": "..." }
  ]
}
```

`movimientos_pendientes_de_justificar` (User Story 3, FR-007/FR-008): cargos (`importe < 0`) de
este extracto sin ninguna factura vinculada.

**Errores**: `404` conciliación no encontrada.

---

## POST /api/candidate-documents/{id}/reconcile

Resuelve manualmente un documento `PENDIENTE REVISIÓN CONCILIACIÓN` (User Story 2, FR-006).

**Request**:
```json
{ "movimiento_id": 15 }
```
`movimiento_id: null` descarta todos los candidatos (el documento pasa a
`NO ENCONTRADA EN EXTRACTO`).

**Response `200 OK`**:
```json
{ "id": 503, "estado_conciliacion": "CONCILIADA", "movimiento_id": 15 }
```

**Errores**:
- `422` el documento no está `PENDIENTE REVISIÓN CONCILIACIÓN`.
- `422` `movimiento_id` no es uno de los candidatos guardados para este documento.

---

## GET /api/candidate-documents/{id} — ampliado

Se añaden (cuando aplican) los campos de conciliación al detalle ya existente (features 001-003):

```json
{
  "...": "campos existentes de las features anteriores",
  "estado_conciliacion": "CONCILIADA",
  "movimiento_conciliado": { "id": 15, "fecha": "2026-07-05", "importe": -120.0, "concepto": "..." }
}
```

`estado_conciliacion` es `null` si el documento no está `PROCESADA` o todavía no se ha aportado
ningún extracto que lo cubra.

---

## Sin cambios

Ningún endpoint de las features 001-003 cambia su comportamiento. Esta feature no toca la
ingesta, la validación/archivado ni las sugerencias.
