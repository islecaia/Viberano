# API Contract: Sugerencia Automática de Datos de Factura

**Fase**: 1 — Design & Contracts
**Spec**: [spec.md](../spec.md) · **Data model**: [data-model.md](../data-model.md)

No se añaden endpoints nuevos (research.md §7). Esta feature amplía la respuesta de un endpoint
ya existente de `specs/002-validacion-archivado-facturas/contracts/api.md`.

## GET /api/candidate-documents/{id} — ampliado

Cuando el documento está en `REVISIÓN MANUAL` y tiene sugerencias con confianza suficiente
(data-model.md), la respuesta incluye un objeto `sugerencia` adicional:

**Response `200 OK`**:
```json
{
  "id": 501,
  "estado": "REVISIÓN MANUAL",
  "motivo_clasificacion": "Adjunto PDF con estructura de factura; proveedor no verificado",
  "remitente": "proveedor@ejemplo.com",
  "asunto": "Factura agosto",
  "fecha_correo": "2026-08-09T08:30:00Z",
  "adjunto_url": "/api/candidate-documents/501/attachment",
  "proveedor": null,
  "sugerencia": {
    "proveedor_nombre": "Suministros Eléctricos Norte",
    "proveedor_id_coincidente": 3,
    "fecha_factura": "2026-08-01",
    "numero_factura": "F-2026-042",
    "total": 123.45
  }
}
```

- `sugerencia` es `null` si no hay ningún campo sugerido con confianza suficiente para este
  documento (FR-003, FR-007).
- Cada campo dentro de `sugerencia` puede ser `null` individualmente (un campo sin confianza
  suficiente no bloquea que se sugieran los demás).
- `proveedor_id_coincidente` es `null` si `proveedor_nombre` no coincide con ningún proveedor ya
  existente en el catálogo (User Story 2) — en ese caso la interfaz debe ofrecerlo como
  "proveedor nuevo", igual que si la persona lo hubiera escrito ella misma en ese campo
  (specs/002-validacion-archivado-facturas/contracts/api.md).
- Para un documento que no está en `REVISIÓN MANUAL`, `sugerencia` es siempre `null` (FR-008),
  independientemente de si se generaron valores en su momento.

## Sin cambios

`POST /api/candidate-documents/{id}/validate` y `POST /api/candidate-documents/{id}/reclassify`
(feature 002) no cambian: la persona sigue enviando exactamente los mismos campos, ahora
precargados por la interfaz a partir de `sugerencia` en vez de partir de un formulario vacío.
