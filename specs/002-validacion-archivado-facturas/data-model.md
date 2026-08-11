# Data Model: Validación y Archivado con Revisión Humana

**Fase**: 1 — Design & Contracts
**Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

Extiende el modelo de datos de `specs/001-ingesta-facturas-email/data-model.md`. Los cambios se
aplican vía `app/db/migrations/0002_validacion_archivado.sql` (research.md §1-§2).

## Proveedor (`providers`) — tabla nueva

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer PK | |
| `nombre` | text | Único (comparación exacta normalizada, research.md §5) |
| `identificador_fiscal` | text nullable | Solo si hay evidencia (Principio I) |
| `activo` | boolean | `true` por defecto al crearse (FR-005) |
| `fecha_alta` | datetime | |

**Validación**: `nombre` único (case-insensitive, espacios normalizados). Desactivar un proveedor
(`activo = false`) no borra ni afecta a los documentos ya `PROCESADA` asociados a él (FR-006,
User Story 2 escenario 2).

## DocumentoCandidato (`candidate_documents`) — columnas nuevas

| Campo nuevo | Tipo | Notas |
|---|---|---|
| `proveedor_id` | integer nullable, FK → `providers.id` | Nulo mientras no se valida |
| `fecha_factura` | date nullable | Introducida/confirmada por la persona autorizada (FR-001) |
| `numero_factura` | text nullable | Ídem |
| `total` | real nullable | Ídem; puede ser negativo solo si `es_nota_credito = true` |
| `es_nota_credito` | boolean | `false` por defecto |
| `validado_por` | text nullable | Identidad de la persona autorizada que confirmó (FR-008) |
| `fecha_validacion` | datetime nullable | Momento de la confirmación (FR-008) |

**`estado`**: el `CHECK` se amplía a `REVISIÓN MANUAL`, `NO ES FACTURA`, `FACTURA DE VENTA`,
`DUPLICADO IGNORADO`, `PROCESADA` (research.md §2). Con esta feature, `PROCESADA` deja de estar
prohibido a nivel de esquema — sigue estando prohibido a nivel de aplicación llegar a él sin
pasar por el flujo de validación (FR-003, FR-004).

**Restricción de unicidad (FR-009, research.md §4)**:

```sql
CREATE UNIQUE INDEX ux_candidate_documents_factura_procesada
    ON candidate_documents (proveedor_id, fecha_factura, numero_factura)
    WHERE estado = 'PROCESADA';
```

Un intento de transicionar a `PROCESADA` que violaría este índice se rechaza antes de escribir
(comprobación explícita en la capa de servicio, con mensaje claro) en vez de dejar que falle como
un error de base de datos genérico.

## Máquina de estados de `DocumentoCandidato` (ampliada respecto a la feature 001)

```
REVISIÓN MANUAL ──(validar 4 campos + proveedor activo + confirmar)──▶ PROCESADA
REVISIÓN MANUAL ──(reclasificar, FR-007)──▶ NO ES FACTURA
REVISIÓN MANUAL ──(reclasificar, FR-007)──▶ FACTURA DE VENTA

PROCESADA, NO ES FACTURA, FACTURA DE VENTA, DUPLICADO IGNORADO → estados finales (FR-011):
ninguna transición sale de ellos dentro de esta feature.
```

**Validación de campos antes de `PROCESADA`** (FR-001 a FR-004):

- `proveedor_id` debe existir y su `providers.activo` debe ser `true` en el momento de confirmar.
- `fecha_factura` debe ser una fecha válida.
- `numero_factura` no puede estar vacío.
- `total` debe ser numérico; si es negativo, `es_nota_credito` debe ser `true` (si no, se rechaza
  como dato inválido, edge case de spec.md).
- La combinación `(proveedor_id, fecha_factura, numero_factura)` no debe coincidir con la de otro
  documento ya `PROCESADA` (índice único de arriba).

Si cualquiera de estas condiciones falla, el documento permanece en `REVISIÓN MANUAL` y la
persona autorizada recibe el motivo concreto (FR-003).

## Relaciones

```
providers 1──* candidate_documents (proveedor_id, solo cuando está validado)
```

El resto de relaciones (mailbox_accounts, sync_runs, ingested_emails) no cambian respecto a
`specs/001-ingesta-facturas-email/data-model.md`.
