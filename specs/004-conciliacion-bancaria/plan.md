# Implementation Plan: Conciliación Bancaria

**Branch**: `004-conciliacion-bancaria` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-conciliacion-bancaria/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Permitir a la persona autorizada aportar un extracto bancario en CSV y comparar cada factura
`PROCESADA` del periodo contra los movimientos, marcando cada una como conciliada (vinculada a un
movimiento inequívoco), "no encontrada en el extracto" (nunca "impagada", Principio VI), o
pendiente de revisión manual si hay varios candidatos igual de plausibles. Enfoque técnico: sin
dependencias nuevas (`csv` estándar + `python-multipart` ya presente); coincidencia determinista
por importe exacto + ventana de fecha + unicidad del candidato (research.md §3), sin IA ni
heurísticas difusas; la conciliación se ejecuta solo cuando la persona aporta el extracto
explícitamente (sin scheduler, Principio V).

## Technical Context

**Language/Version**: Python 3.11+ (mismo proyecto que las features 001-003)

**Primary Dependencies**: Ninguna dependencia nueva — `csv` (estándar) para parsear el extracto,
`python-multipart` (ya presente desde la feature 001) para la subida del archivo.

**Storage**: SQLite (mismo mecanismo de migraciones versionadas). Migración `0004`: dos tablas
nuevas (`bank_statements`, `bank_movements`, `reconciliation_candidates`) y dos columnas nuevas en
`candidate_documents` (`estado_conciliacion`, `movimiento_bancario_id`) — solo `ADD COLUMN`
nullable, sin recrear ninguna tabla (mismo caso que la migración `0003`).

**Testing**: pytest + pytest-asyncio (mismo criterio que las features anteriores); sin tests
dedicados salvo que se solicite explícitamente.

**Target Platform**: la misma app web única — no se añade ningún componente desplegable nuevo.

**Project Type**: extensión del proyecto único ya existente (`app/`).

**Performance Goals**: procesar un extracto de hasta 200 movimientos y mostrar el resultado
completo en menos de 1 minuto (SC-001).

**Constraints**: ninguna factura se marca como impagada — solo conciliada, no encontrada en el
extracto, o pendiente de revisión manual (FR-004, Principio VI); ninguna coincidencia ambigua se
resuelve automáticamente (FR-005); sin ninguna conciliación automática o recurrente (FR-010,
Principio V); un extracto inválido se rechaza sin tocar ninguna factura (FR-011).

**Scale/Scope**: una sola cuenta bancaria y una sola divisa (spec.md, Assumptions); mismo alcance
de usuario único/pocas personas autorizadas que el resto del proyecto.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / Sección | Estado | Cómo lo cumple el diseño |
|---|---|---|
| I. No Invención de Datos | PASS | Una coincidencia solo se confirma automáticamente cuando es el único candidato exacto (research.md §3); ante ambigüedad, nunca se elige por adivinanza — queda pendiente (FR-005). |
| II. Validación Obligatoria Antes de Archivar | N/A | Esta feature no archiva nada nuevo; solo añade metadato de conciliación sobre documentos que ya están `PROCESADA` (feature 002). |
| III. Inmutabilidad de Originales | PASS | No se toca ningún correo ni adjunto original; el extracto aportado se guarda como datos, no se reinterpreta (data-model.md). |
| IV. No Sobrescritura de Archivos | PASS | Ningún movimiento ni extracto se sobrescribe tras su creación (data-model.md § BankMovement). |
| V. Control Humano Explícito | PASS | La conciliación solo se ejecuta al llamar `POST /api/reconciliations` explícitamente; sin scheduler (FR-010, research.md §1). |
| VI. Precisión en Estados de Conciliación | PASS | Es el propósito central de la feature: FR-004 y el Escenario 2 de quickstart.md implementan literalmente el principio. |
| VII. Uso Acotado de IA de Pago | PASS (N/A ampliado) | Esta feature no usa la Anthropic API ni ningún otro modelo — el matching es determinista (research.md §3). |
| Autenticación y Control de Acceso | PASS | Los endpoints nuevos quedan bajo el mismo `api_router` protegido por sesión de persona autorizada. |
| Sistema de Diseño | PASS (aplica a la UI) | La pantalla de Conciliación (sustituye el placeholder de la barra inferior) debe seguir Montserrat, `#0062FF`, tarjetas 12px. |

No hay violaciones que requieran justificación en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── db/
│   └── migrations/
│       └── 0004_conciliacion_bancaria.sql   # bank_statements, bank_movements,
│                                              # reconciliation_candidates + columnas nuevas
├── models/
│   ├── bank_statement.py           # nuevo
│   ├── bank_movement.py            # nuevo (incluye consultas de candidatos/pendientes)
│   └── candidate_document.py       # + estado_conciliacion, movimiento_bancario_id
├── services/
│   └── reconciliation_service.py   # nuevo: parseo CSV, matching, orquestación
├── api/routes/
│   ├── reconciliations.py          # nuevo: POST/GET /api/reconciliations
│   └── candidate_documents.py      # + POST .../reconcile, GET .../{id} ampliado
└── templates/
    └── reconciliation.html         # nuevo: sustituye el placeholder de /conciliacion

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: se extiende el mismo proyecto único de las features 001-003 (`app/`); no
se crea ningún componente nuevo desplegable.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No aplica: el Constitution Check no registra ninguna violación (todas las filas son PASS o N/A).
