# Data Model: Conciliación Bancaria

**Fase**: 1 — Design & Contracts
**Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

Se aplica vía `app/db/migrations/0004_conciliacion_bancaria.sql`: dos tablas nuevas y dos
columnas nuevas en `candidate_documents` (ya existente desde la feature 001, ampliada en 002 y
003).

## BankStatement (`bank_statements`) — tabla nueva

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer PK | |
| `fecha_inicio` | date | Mínimo de `fecha` entre sus movimientos (research.md §1) |
| `fecha_fin` | date | Máximo de `fecha` entre sus movimientos |
| `aportado_por` | text | Persona autorizada que lo aportó (FR-001) |
| `fecha_aporte` | datetime | |
| `total_movimientos` | integer | Recuento, para mostrar en el resumen |

## BankMovement (`bank_movements`) — tabla nueva

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer PK | |
| `extracto_id` | integer, FK → `bank_statements.id` | |
| `fecha` | date | |
| `importe` | real | Positivo = ingreso, negativo = cargo (research.md §5) |
| `concepto` | text | |

**Validación**: ningún campo se modifica tras la creación — un movimiento es una copia fiel de
una fila del CSV aportado (Principio I: no se reinterpreta el dato original).

## DocumentoCandidato (`candidate_documents`) — columnas nuevas

| Campo nuevo | Tipo | Notas |
|---|---|---|
| `estado_conciliacion` | text nullable | `NULL` (todavía no evaluada), `CONCILIADA`, `NO ENCONTRADA EN EXTRACTO`, `PENDIENTE REVISIÓN CONCILIACIÓN` |
| `movimiento_bancario_id` | integer nullable, FK → `bank_movements.id` | Solo relleno cuando `estado_conciliacion = 'CONCILIADA'` |

**Regla**: estos campos solo se evalúan para documentos en `estado = 'PROCESADA'` (FR-002); un
documento en cualquier otro estado nunca tiene `estado_conciliacion` distinto de `NULL`.

**Estabilidad (research.md §4)**: una vez que `estado_conciliacion` es `CONCILIADA` o
`NO ENCONTRADA EN EXTRACTO`, ninguna conciliación posterior lo vuelve a evaluar (spec.md,
Assumptions) — evita duplicar vínculos sin necesitar deduplicar movimientos en bruto.

## ReconciliationCandidate (`reconciliation_candidates`) — tabla nueva, solo para casos ambiguos

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer PK | |
| `documento_id` | integer, FK → `candidate_documents.id` | Solo mientras esté `PENDIENTE REVISIÓN CONCILIACIÓN` |
| `movimiento_id` | integer, FK → `bank_movements.id` | Uno de los varios candidatos posibles (research.md §3) |

**Ciclo de vida**: se crean varias filas (una por candidato) cuando FR-005 detecta ambigüedad; al
resolverse (FR-006), todas las filas de ese `documento_id` se eliminan — o bien
`candidate_documents.movimiento_bancario_id` queda relleno (se eligió un candidato) o
`estado_conciliacion` pasa a `NO ENCONTRADA EN EXTRACTO` (se descartaron todos).

## Máquina de estados de `estado_conciliacion`

```
NULL ──(ejecutar conciliación, único candidato)────────────▶ CONCILIADA
NULL ──(ejecutar conciliación, cero candidatos)─────────────▶ NO ENCONTRADA EN EXTRACTO
NULL ──(ejecutar conciliación, varios candidatos)───────────▶ PENDIENTE REVISIÓN CONCILIACIÓN
PENDIENTE REVISIÓN CONCILIACIÓN ──(persona elige uno)───────▶ CONCILIADA
PENDIENTE REVISIÓN CONCILIACIÓN ──(persona descarta todos)──▶ NO ENCONTRADA EN EXTRACTO

CONCILIADA y NO ENCONTRADA EN EXTRACTO son estables (research.md §4): ninguna conciliación
posterior transiciona un documento que ya está en uno de esos dos estados.
```

## Relaciones

```
bank_statements 1──* bank_movements
bank_movements 1──? candidate_documents (movimiento_bancario_id, solo si CONCILIADA)
candidate_documents 1──* reconciliation_candidates (solo si PENDIENTE REVISIÓN CONCILIACIÓN)
reconciliation_candidates *──1 bank_movements
```
