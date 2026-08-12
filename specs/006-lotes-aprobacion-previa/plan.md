# Implementation Plan: Lotes con Aprobación Previa y Reanudación

**Branch**: `006-lotes-aprobacion-previa` | **Date**: 2026-08-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-lotes-aprobacion-previa/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Divide la sincronización (feature 001) en dos fases explícitas: **analizar** (lee el buzón,
guarda cada correo nuevo y sus adjuntos candidatos sin clasificarlos ni crear documentos
candidato, y muestra un resumen) y **ejecutar** (clasifica y crea los documentos candidato,
solo tras aprobación explícita de la persona autorizada). La fase de ejecución procesa cada
correo en su propio try/except — un fallo puntual no aborta el resto del lote (a diferencia del
catch-all introducido en la revisión de código anterior, que sigue existiendo como red de
seguridad para fallos sistémicos) — y un único endpoint de ejecución sirve tanto para aprobar el
lote la primera vez, como para reanudarlo tras una interrupción, como para reintentar los correos
que fallaron: en los tres casos simplemente procesa lo que siga `PENDIENTE`/`FALLIDO` de ese lote.

## Technical Context

**Language/Version**: Python 3.11+ (mismo proyecto que las features 001-005)

**Primary Dependencies**: Ninguna dependencia nueva — reutiliza `imaplib`/`email` (feature 001),
`anthropic`/`pypdf` (clasificación, features 001/003) y `attachment_store` ya existente.

**Storage**: SQLite. Migración `0005`: recrea `sync_runs` (BEGIN/COMMIT, patrón de la migración
`0002`) para ampliar su `CHECK` de `estado` con `'pendiente_aprobacion'` y añadir dos columnas de
resumen (`correos_nuevos_detectados`, `correos_con_adjuntos_candidatos`); amplía el índice único
parcial de "una sincronización activa por cuenta" para cubrir también `pendiente_aprobacion`;
añade a `ingested_emails` (`ADD COLUMN` simple, sin recrear) `estado_procesamiento` y
`motivo_fallo`; crea la tabla nueva `pending_attachments` para los adjuntos ya guardados pero
todavía sin clasificar. Se aplican las lecciones de la revisión de código: toda la migración
queda envuelta en `BEGIN/COMMIT` (research.md §3).

**Testing**: pytest disponible; sin tests dedicados salvo que se solicite explícitamente (mismo
criterio que las features 001-005) — verificación funcional vía script en proceso + los
escenarios de quickstart.md.

**Target Platform**: la misma app web única — no se añade ningún componente desplegable nuevo ni
procesamiento en segundo plano (la ejecución sigue siendo síncrona dentro de la petición HTTP,
igual que la sincronización actual).

**Project Type**: extensión del proyecto único ya existente (`app/`).

**Performance Goals**: analizar un lote típico (buzón con actividad de un día) en el mismo orden
de magnitud que la sincronización actual, ya que la fase de análisis hace el mismo trabajo IMAP
que hoy — solo difiere la clasificación (IA), no la lectura del buzón.

**Constraints**: ningún documento candidato se crea sin aprobación explícita del lote (FR-003);
ningún fallo de un correo concreto bloquea el resto del lote (FR-009); solo un lote pendiente de
aprobación o en ejecución por cuenta a la vez (FR-005); la aprobación, la ejecución y el
reintento son siempre acciones explícitas de la persona autorizada (FR-012, Principio V).

**Scale/Scope**: mismo alcance de una cuenta de correo por persona autorizada que el resto del
proyecto; no introduce procesamiento paralelo ni colas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / Sección | Estado | Cómo lo cumple el diseño |
|---|---|---|
| I. No Invención de Datos | PASS | El resumen del lote cuenta correos y adjuntos reales identificados por tipo de archivo; no se infiere ni estima nada sobre su contenido antes de clasificarlos (research.md §1). |
| II. Validación Obligatoria Antes de Archivar | PASS (N/A ampliado) | "Aprobar un lote" solo autoriza la clasificación y creación de documentos candidato (mismos estados que hoy: REVISIÓN MANUAL, NO ES FACTURA, etc.) — nunca crea directamente un documento PROCESADA; la validación individual de la feature 002 sigue exigiéndose igual que hoy (spec.md, Assumptions). |
| III. Inmutabilidad de Originales | PASS | Los adjuntos se guardan sin modificar en cuanto se identifican, igual que hoy (`attachment_store`); `pending_attachments` solo referencia esa copia, no la duplica. |
| IV. No Sobrescritura de Archivos | PASS | Mismo mecanismo de `attachment_store` ya existente (research.md §2); ninguna escritura nueva sobrescribe una anterior. |
| V. Control Humano Explícito | PASS | Refuerza el principio respecto a hoy: el análisis sigue siendo una acción explícita, y ahora la clasificación/creación de candidatos exige una **segunda** acción explícita (aprobar) que hoy no existe. |
| VI. Precisión en Estados de Conciliación | N/A | Esta feature no toca conciliación bancaria. |
| VII. Uso Acotado de IA de Pago | PASS | Refuerza el principio: la única llamada a la Anthropic API (clasificación) se difiere hasta que la persona aprueba el lote explícitamente, dándole control adicional sobre cuándo se genera ese coste (research.md §1). |
| Autenticación y Control de Acceso | PASS | Los endpoints nuevos quedan bajo el mismo `api_router` protegido por sesión de persona autorizada. |
| Sistema de Diseño | PASS (aplica a la UI) | La pantalla de Facturas gana el estado "pendiente de aprobación" del lote, siguiendo Montserrat, `#0062FF`, tarjetas de 12px, igual que el resto de pantallas. |

No hay violaciones que requieran justificación en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/006-lotes-aprobacion-previa/
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
│       └── 0005_lotes_aprobacion_previa.sql   # sync_runs ampliada, ingested_emails + 2 cols,
│                                                 # pending_attachments (tabla nueva)
├── models/
│   ├── sync_run.py             # + estados 'pendiente_aprobacion', resumen, create_analisis()
│   ├── ingested_email.py       # + estado_procesamiento/motivo_fallo, marcar_procesado/fallido
│   └── pending_attachment.py   # nuevo: create(), list_for_correo(), delete()
├── services/
│   └── sync_service.py         # separa analizar_lote() de ejecutar_lote(); try/except por correo
├── api/routes/
│   └── sync_runs.py            # + POST .../sync/{id}/execute; GET ampliado con resumen/fallidos
└── templates/
    └── candidates_list.html    # + tarjeta de lote pendiente/con fallos y sus acciones

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: se extiende el mismo proyecto único de las features 001-005 (`app/`); no
se crea ningún componente nuevo desplegable ni procesamiento en segundo plano.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No aplica: el Constitution Check no registra ninguna violación (todas las filas son PASS o N/A).
