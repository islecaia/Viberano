# Implementation Plan: Validación y Archivado con Revisión Humana

**Branch**: `002-validacion-archivado-facturas` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-validacion-archivado-facturas/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Sobre la app ya construida en `specs/001-ingesta-facturas-email/`, añadir un flujo de validación
humana para los documentos candidatos en REVISIÓN MANUAL: introducir/confirmar proveedor
(activo), fecha, número y total, y confirmar explícitamente el archivado, momento en el que el
documento pasa a PROCESADA. Incluye un catálogo mínimo de proveedores (activo/inactivo) y la
posibilidad de reclasificar un documento como NO ES FACTURA o FACTURA DE VENTA sin pasar por la
validación completa. Enfoque técnico: se extiende el mismo esquema SQLite mediante un mecanismo
de migraciones versionadas (research.md §1-§2, necesario para añadir PROCESADA al CHECK de
`estado`), un índice único parcial evita archivados duplicados sin reorganizar archivos físicos
(research.md §4), y no se introduce ningún uso nuevo de IA (esta feature es 100% manual).

## Technical Context

**Language/Version**: Python 3.11+ (mismo proyecto que specs/001-ingesta-facturas-email/)

**Primary Dependencies**: FastAPI, Jinja2, `sqlite3` estándar (sin dependencias nuevas — no se
necesita ninguna librería adicional para esta feature).

**Storage**: SQLite en modo WAL (ya establecido). Se introduce un mecanismo de migraciones
versionadas en `app/db/migrations/` (research.md §1) porque esta feature necesita cambiar el
`CHECK` de `candidate_documents.estado` (research.md §2), algo que el `schema.sql` único de la
feature 001 no podía hacer sobre una base de datos ya existente.

**Testing**: pytest + pytest-asyncio (igual que la feature 001); sin tests dedicados en esta
feature salvo que se solicite explícitamente (mismo criterio que specs/001-ingesta-facturas-email/tasks.md).

**Target Platform**: el mismo servidor/una sola app web que la feature 001 — no se añade ningún
componente nuevo desplegable.

**Project Type**: extensión del proyecto único ya existente (`app/`) — no se crea una segunda
aplicación ni servicio.

**Performance Goals**: validar y archivar un documento completo en menos de 2 minutos (SC-001);
sin requisitos de volumen nuevos respecto a la feature 001.

**Constraints**: ningún documento pasa a PROCESADA sin los cuatro campos, proveedor activo y
confirmación humana explícita (FR-001 a FR-004); nunca se sobrescribe un archivado existente
(FR-009); los estados finales (PROCESADA, NO ES FACTURA, FACTURA DE VENTA) no se reabren dentro
de esta feature (FR-011).

**Scale/Scope**: mismo alcance de usuario único/pocas personas autorizadas que la feature 001;
un catálogo de proveedores del orden de decenas a un centenar de entradas para una microempresa.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / Sección | Estado | Cómo lo cumple el diseño |
|---|---|---|
| I. No Invención de Datos | PASS | FR-001: proveedor/fecha/número/total siempre los introduce o confirma la persona autorizada; el sistema nunca los completa por su cuenta. El identificador fiscal del proveedor es opcional y solo si hay evidencia. |
| II. Validación Obligatoria Antes de Archivar | PASS | Es el propósito central de la feature: FR-002/FR-003/FR-004 impiden PROCESADA sin los cuatro campos y proveedor activo. |
| III. Inmutabilidad de Originales | PASS | El adjunto original gestionado por la feature 001 (attachment_store) no se toca; archivar es solo cambio de estado + metadatos (research.md §4). |
| IV. No Sobrescritura de Archivos | PASS | research.md §4: índice único parcial sobre (proveedor_id, fecha_factura, numero_factura) para PROCESADA; una colisión se rechaza (409) en vez de sobrescribir. |
| V. Control Humano Explícito | PASS | `POST /api/candidate-documents/{id}/validate` exige una llamada explícita de la persona autorizada; sin scheduler ni aprobación automática. |
| VI. Precisión en Estados de Conciliación | N/A | Conciliación bancaria fuera de alcance de esta feature (ver spec.md). |
| VII. Uso Acotado de IA de Pago | PASS (N/A ampliado) | Esta feature no introduce ningún uso nuevo de Anthropic API ni de ningún otro modelo — el proceso es 100% de revisión humana. |
| Autenticación y Control de Acceso | PASS | Reutiliza la sesión de persona autorizada de la feature 001 (research.md §6); los endpoints nuevos quedan bajo el mismo `api_router` protegido. |
| Sistema de Diseño | PASS (aplica a M-UI) | La pantalla de validación (extensión de `candidate_detail.html`) y la nueva pantalla de Proveedores (sustituye el placeholder de la feature 001) deben seguir Montserrat, `#0062FF`, tarjetas 12px y la barra de navegación inferior ya existente. |

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
│   ├── migrations/
│   │   ├── 0001_initial.sql        # schema.sql de la feature 001, renombrado sin cambios
│   │   └── 0002_validacion_archivado.sql   # tabla providers + columnas nuevas + CHECK ampliado
│   └── session.py                  # + lógica de aplicar migraciones pendientes (research.md §1)
├── models/
│   ├── provider.py                 # nuevo
│   └── candidate_document.py       # + campos y transición a PROCESADA/reclasificación
├── services/
│   └── validation_service.py       # nuevo: valida los 4 campos, proveedor activo, colisión
├── api/routes/
│   ├── providers.py                 # nuevo: POST/GET /api/providers, PATCH /api/providers/{id}
│   └── candidate_documents.py       # + POST .../validate, POST .../reclassify
└── templates/
    ├── candidate_detail.html        # + formulario de validación y botones de reclasificación
    └── providers.html                # nuevo: sustituye el placeholder de /proveedores

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: se extiende el mismo proyecto único de `specs/001-ingesta-facturas-email/`
(`app/`); no se crea ninguna aplicación ni servicio nuevo. La única pieza de infraestructura
nueva es `app/db/migrations/`, necesaria por research.md §1-§2.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No aplica: el Constitution Check no registra ninguna violación (todas las filas son PASS o N/A).
