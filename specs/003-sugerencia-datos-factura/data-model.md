# Data Model: Sugerencia Automática de Datos de Factura

**Fase**: 1 — Design & Contracts
**Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

Extiende `candidate_documents` (definida en `specs/001-ingesta-facturas-email/data-model.md`,
ampliada en `specs/002-validacion-archivado-facturas/data-model.md`) vía
`app/db/migrations/0003_sugerencia_datos_factura.sql` (research.md §4).

## DocumentoCandidato (`candidate_documents`) — columnas nuevas

| Campo nuevo | Tipo | Notas |
|---|---|---|
| `sugerido_proveedor_nombre` | text nullable | Nombre de proveedor identificado en el documento; `NULL` si no hubo confianza suficiente (FR-003) |
| `sugerido_fecha_factura` | text nullable (fecha ISO) | Ídem |
| `sugerido_numero_factura` | text nullable | Ídem |
| `sugerido_total` | real nullable | Ídem |

**Reglas**:

- Estas cuatro columnas se rellenan una única vez, en el momento en que se crea el documento
  candidato (research.md §2) — nunca se actualizan después.
- No existe columna de confianza persistida: el umbral ya se aplicó antes de guardar
  (research.md §3); un campo por debajo del umbral simplemente queda `NULL`.
- No hay relación directa con `providers`: `sugerido_proveedor_nombre` es texto libre que se
  resuelve contra el catálogo en el momento de mostrarse (research.md §6), nunca se persiste como
  `proveedor_id`.
- Estas columnas son puramente informativas para la pantalla de validación: `POST
  /api/candidate-documents/{id}/validate` (feature 002) no las lee ni las usa — solo lee el
  `payload` que envía la persona, que puede o no coincidir con lo sugerido.

## Relación con el flujo existente

```
Ingesta (feature 001) → clasifica documento → (NUEVO) además calcula sugerencias en la misma
  llamada → guarda candidate_documents con estado + motivo + sugerido_* (si hay confianza)

Validación (feature 002) → GET /api/candidate-documents/{id} devuelve también los sugerido_*
  cuando existen → la pantalla los precarga → la persona confirma/corrige → POST .../validate
  (sin cambios, ver contracts/api.md)
```

No hay ninguna máquina de estados nueva: los estados de `candidate_documents` siguen siendo
exactamente los definidos en la feature 002.
