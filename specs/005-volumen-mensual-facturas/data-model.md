# Data Model: Volumen Mensual de Facturas

**Fase**: 1 — Design & Contracts
**Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

No se aplica ninguna migración: esta feature es de solo lectura sobre columnas ya existentes
(`app/db/migrations/0001_initial.sql`, `0002_...`). No hay ninguna tabla ni columna nueva.

## Fuentes de datos leídas (ya existentes)

| Tabla.Columna | Origen | Uso en esta feature |
|---|---|---|
| `candidate_documents.estado` | feature 001 | Filtrar solo `PROCESADA` (FR-002) |
| `candidate_documents.fecha_factura` | feature 002 | Agrupar por año-mes (FR-003) |
| `mailbox_accounts.fecha_conexion` | feature 001 | Determinar si el primer mes del periodo es parcial (research.md §2) |

## Recuento Mensual — agregación calculada, no persistida

| Campo | Tipo | Notas |
|---|---|---|
| `mes` | text `YYYY-MM` | Año-mes agrupado por `fecha_factura` |
| `total` | integer | Número de facturas `PROCESADA` con `fecha_factura` en ese mes; `0` si ninguna (FR-005) |
| `completo` | boolean | `false` si es el mes en curso o el mes de conexión de la cuenta con conexión posterior al día 1 (research.md §2); `true` en cualquier otro caso |

## Media del Periodo — agregación calculada, no persistida

| Campo | Tipo | Notas |
|---|---|---|
| `media_meses_completos` | float \| null | Media de `total` sobre los meses con `completo = true`; `null` si el periodo no tiene ningún mes completo |
| `media_con_mes_parcial` | float \| null | Media de `total` sobre todos los meses del periodo (completos + parciales); igual a `media_meses_completos` si no hay ningún mes parcial en el periodo — en ese caso el cliente solo necesita mostrar un valor (FR-007, Acceptance Scenario 1) |

**Regla (FR-008)**: `media_meses_completos` nunca incluye un mes con `completo = false` en su
cálculo; un mes parcial solo puede influir en `media_con_mes_parcial`.

## Relaciones

```
candidate_documents (estado='PROCESADA', agrupadas por fecha_factura) ──▶ Recuento Mensual (por mes)
mailbox_accounts.fecha_conexion ──▶ determina qué Recuento Mensual tiene completo=false al inicio
fecha actual del sistema ──▶ determina qué Recuento Mensual tiene completo=false al final
Recuento Mensual (lista) ──▶ Media del Periodo (agregado sobre la lista)
```
