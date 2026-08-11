# Implementation Plan: Sugerencia Automática de Datos de Factura

**Branch**: `003-sugerencia-datos-factura` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-sugerencia-datos-factura/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Precargar el formulario de validación (feature 002) con proveedor, fecha, número y total
propuestos a partir del propio documento, para reducir el trabajo manual de la revisión sin
cambiar ninguna de sus garantías. Enfoque técnico: se amplía el mismo prompt y la misma llamada a
Anthropic API que ya hace la clasificación (feature 001) para que también devuelva los cuatro
campos sugeridos con su confianza — sin añadir una segunda llamada (Principio VII). Las
sugerencias se calculan una única vez, al ingerir el documento, y se guardan en cuatro columnas
nuevas nullable; un campo sin confianza suficiente queda `NULL` en vez de guardarse con un valor
supuesto. No se añade ningún endpoint nuevo: `GET /api/candidate-documents/{id}` simplemente
devuelve también estos campos cuando existen.

## Technical Context

**Language/Version**: Python 3.11+ (mismo proyecto que las features 001 y 002)

**Primary Dependencies**: Ninguna dependencia nueva — se reutiliza el cliente de Anthropic API
(`anthropic`) ya presente desde la feature 001.

**Storage**: SQLite (mismo mecanismo de migraciones versionadas de la feature 002). Esta
migración (`0003`) es más simple que la `0002`: solo añade columnas nullable con `ALTER TABLE ...
ADD COLUMN`, sin necesidad de recrear ninguna tabla (research.md §4).

**Testing**: pytest + pytest-asyncio (mismo criterio que las features 001 y 002); sin tests
dedicados salvo que se solicite explícitamente.

**Target Platform**: la misma app web única — no se añade ningún componente desplegable nuevo.

**Project Type**: extensión del proyecto único ya existente (`app/`).

**Performance Goals**: reducir el tiempo de validación un 30% respecto al tiempo de referencia de
la feature 002 (SC-002); sin impacto en el tiempo de sincronización más allá del ya existente
(la llamada a Anthropic API es la misma, solo con una respuesta algo más larga).

**Constraints**: no se añade ninguna llamada nueva a la Anthropic API (Principio VII, research.md
§1); un campo sugerido con confianza insuficiente nunca se guarda ni se muestra (Principio I,
FR-003); ninguna sugerencia archiva un documento sin confirmación humana explícita (FR-005,
reutiliza la confirmación ya exigida por la feature 002).

**Scale/Scope**: mismo alcance que las features 001 y 002 — el cambio es de precisión/UX sobre el
mismo volumen de documentos, no de escala.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / Sección | Estado | Cómo lo cumple el diseño |
|---|---|---|
| I. No Invención de Datos | PASS | Un campo sin confianza suficiente queda `NULL`, nunca se rellena con una suposición (FR-003, research.md §3). Una sugerencia sigue siendo eso — la persona debe confirmarla o corregirla. |
| II. Validación Obligatoria Antes de Archivar | PASS | `POST /api/candidate-documents/{id}/validate` (feature 002) no cambia: sigue siendo la única vía a PROCESADA, y sigue exigiendo los cuatro campos y proveedor activo, precargados o no. |
| III. Inmutabilidad de Originales | PASS | La generación de sugerencias solo lee el texto ya extraído del adjunto (mismo mecanismo de la feature 001); no toca el correo ni el adjunto original. |
| IV. No Sobrescritura de Archivos | N/A | Esta feature no escribe archivos nuevos; solo añade columnas de base de datos y precarga un formulario. |
| V. Control Humano Explícito | PASS | Ninguna sugerencia archiva nada por sí sola (FR-005); sigue haciendo falta la misma confirmación explícita de la feature 002, incluso con todos los campos sugeridos y de alta confianza (quickstart.md Escenario 3). |
| VI. Precisión en Estados de Conciliación | N/A | Conciliación bancaria fuera de alcance. |
| VII. Uso Acotado de IA de Pago | PASS | research.md §1: se amplía la respuesta de la llamada de clasificación ya existente y ya contabilizada; no se añade ninguna llamada nueva a la Anthropic API. |
| Autenticación y Control de Acceso | PASS | No se añade ningún endpoint; los datos sugeridos viajan dentro de una respuesta ya protegida por la sesión de persona autorizada existente. |
| Sistema de Diseño | PASS (aplica a la UI) | La marca visual de "sugerido" en `candidate_detail.html` debe seguir la paleta y tipografía ya establecidas (Montserrat, `#0062FF`, tarjetas 12px). |

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
│       └── 0003_sugerencia_datos_factura.sql   # 4 columnas nullable en candidate_documents
├── models/
│   └── candidate_document.py       # + campos sugerido_* en CandidateDocument, create() los acepta
├── services/
│   ├── classification.py           # classify() amplía el prompt/respuesta con sugerencias
│   └── sync_service.py             # pasa las sugerencias devueltas a CandidateDocument.create()
├── api/routes/
│   └── candidate_documents.py      # GET .../{id} incluye "sugerencia" en la respuesta
└── templates/
    └── candidate_detail.html       # precarga el formulario con los valores sugeridos

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: se extiende el mismo proyecto único de las features 001 y 002 (`app/`);
no se crea ningún componente nuevo. El cambio más relevante es interno a
`classification.py`/`sync_service.py` (feature 001) y a la presentación en
`candidate_detail.html` (feature 002) — no hay una capa nueva de la aplicación.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No aplica: el Constitution Check no registra ninguna violación (todas las filas son PASS o N/A).
