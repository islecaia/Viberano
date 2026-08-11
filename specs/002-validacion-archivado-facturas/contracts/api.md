# API Contract: Validación y Archivado con Revisión Humana

**Fase**: 1 — Design & Contracts
**Spec**: [spec.md](../spec.md) · **Data model**: [data-model.md](../data-model.md)

Todos los endpoints requieren sesión de persona autorizada activa (heredado de
`specs/001-ingesta-facturas-email/contracts/api.md`). Amplía esos contratos; no los reemplaza.

## POST /api/providers

Crea un proveedor (User Story 2, FR-005).

**Request**:
```json
{ "nombre": "Suministros Eléctricos Norte", "identificador_fiscal": "B12345678" }
```

**Response `201 Created`**:
```json
{ "id": 1, "nombre": "Suministros Eléctricos Norte", "identificador_fiscal": "B12345678", "activo": true }
```

**Errores**: `409` ya existe un proveedor con ese nombre (comparación exacta normalizada,
research.md §5).

---

## GET /api/providers

Lista el catálogo de proveedores (User Story 2).

**Query params**: `activo` (opcional, `true`/`false`).

**Response `200 OK`**:
```json
{ "items": [ { "id": 1, "nombre": "Suministros Eléctricos Norte", "identificador_fiscal": "B12345678", "activo": true } ] }
```

---

## PATCH /api/providers/{id}

Activa o desactiva un proveedor (FR-006).

**Request**: `{ "activo": false }`

**Response `200 OK`**: el proveedor actualizado (mismo formato que `POST /api/providers`).

**Errores**: `404` proveedor no encontrado.

---

## POST /api/candidate-documents/{id}/validate

Valida los cuatro campos y confirma el archivado (User Story 1, FR-001 a FR-004, FR-008).

**Request**:
```json
{
  "proveedor_id": 1,
  "proveedor_nombre_nuevo": null,
  "fecha_factura": "2026-08-01",
  "numero_factura": "F-2026-042",
  "total": 123.45,
  "es_nota_credito": false
}
```

> `proveedor_id` o `proveedor_nombre_nuevo` (no ambos): si el proveedor no existe todavía, se
> puede crear en la misma llamada pasando `proveedor_nombre_nuevo` en vez de `proveedor_id`
> (User Story 2 escenario 3) — queda activo por defecto.

**Response `200 OK`**:
```json
{
  "id": 501,
  "estado": "PROCESADA",
  "proveedor": { "id": 1, "nombre": "Suministros Eléctricos Norte" },
  "fecha_factura": "2026-08-01",
  "numero_factura": "F-2026-042",
  "total": 123.45,
  "es_nota_credito": false,
  "validado_por": "isleca@protonmail.com",
  "fecha_validacion": "2026-08-11T10:00:00Z"
}
```

**Errores**:
- `422` falta algún campo obligatorio, `total` no numérico, o `total` negativo sin
  `es_nota_credito: true` (edge case de spec.md).
- `409` el proveedor indicado no está activo (FR-002/FR-003) — el cuerpo incluye
  `proveedor_id` para que la interfaz pueda ofrecer activarlo (User Story 1 escenario 3).
- `409` el documento ya no está en `REVISIÓN MANUAL` (edge case de condición de carrera).
- `409` ya existe otro documento `PROCESADA` con el mismo proveedor + fecha + número
  (data-model.md, índice único) — el cuerpo indica el `id` del documento en conflicto.

---

## POST /api/candidate-documents/{id}/reclassify

Reclasifica un documento en `REVISIÓN MANUAL` sin pasar por los cuatro campos (User Story 3,
FR-007).

**Request**:
```json
{ "estado": "NO ES FACTURA" }
```
`estado` debe ser `"NO ES FACTURA"` o `"FACTURA DE VENTA"`.

**Response `200 OK`**:
```json
{ "id": 501, "estado": "NO ES FACTURA" }
```

**Errores**:
- `422` `estado` no es uno de los dos valores permitidos aquí.
- `409` el documento ya no está en `REVISIÓN MANUAL` (FR-011: son estados finales).

---

## Fuera de alcance de este contrato

Ningún endpoint permite revertir un documento desde `PROCESADA`, `NO ES FACTURA` o
`FACTURA DE VENTA` a otro estado (FR-011); tampoco existe edición ni fusión avanzada de
proveedores (spec.md, Assumptions).
