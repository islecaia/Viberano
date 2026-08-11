# Implementation Plan: Ingesta y Detección de Facturas por Email

**Branch**: `001-ingesta-facturas-email` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-ingesta-facturas-email/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Conectar una cuenta de correo (Gmail API, IMAP genérico o Microsoft Graph) y, mediante una
sincronización manual, detectar qué correos contienen probablemente una factura de gasto,
extrayendo sus adjuntos (PDF/JPG/PNG) como documentos candidatos clasificados en REVISIÓN MANUAL,
NO ES FACTURA, FACTURA DE VENTA o DUPLICADO IGNORADO — sin archivar nada automáticamente. El
enfoque técnico: FastAPI expone una API + UI server-rendered sobre SQLite; un filtro de formato de
adjunto acota qué correos llegan a una clasificación con Anthropic API (uso acotado, ver
research.md §4); cada adjunto se copia a un almacén de solo lectura para no tocar nunca el
original (Principios III y IV); la sincronización solo se dispara por acción humana explícita
(Principio V).

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI, Jinja2 (UI server-rendered, sin framework JS adicional),
SQLAlchemy Core o `sqlite3` para acceso a datos, cliente Gmail API, `imaplib` (IMAP genérico),
SDK de Microsoft Graph, cliente de Anthropic API (uso acotado a clasificación, Principio VII), uv
como gestor de dependencias/entorno.

**Storage**: SQLite en modo WAL (research.md §7) para metadatos (cuentas, sincronizaciones,
correos ingeridos, documentos candidatos); adjuntos originales copiados a un almacén de archivos
de solo lectura en disco, referenciados por ruta desde SQLite (research.md §3).

**Testing**: pytest + pytest-asyncio (rutas FastAPI), con un `MailboxConnector` fake/IMAP local de
pruebas (research.md §1) para no depender de credenciales reales de Gmail/Graph en CI.

**Target Platform**: servidor Linux (contenedor) sirviendo una web app responsive vía navegador
(desktop y móvil); sin app nativa, sin modo offline (según constitution).

**Project Type**: aplicación web con backend único (FastAPI sirve tanto la API como la UI
server-rendered) — estructura de proyecto única, sin frontend separado.

**Performance Goals**: sincronizar 100 correos nuevos en menos de 2 minutos (SC-004); primera
lista de candidatos visible en menos de 5 minutos tras conectar la cuenta (SC-001).

**Constraints**: ningún documento pasa a PROCESADA sin decisión humana explícita (fuera del
alcance de esta feature); REVISIÓN MANUAL por defecto ante cualquier incertidumbre de
clasificación; correos y adjuntos originales intactos siempre; sincronización disparada solo de
forma manual, sin tareas programadas ni jobs en segundo plano.

**Scale/Scope**: una persona autorizada, una cuenta de correo conectada por persona (Assumption de
spec.md), volumen esperado de decenas a cientos de correos/mes propio de autónomos y
microempresas, ventana de importación inicial de 90 días.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / Sección | Estado | Cómo lo cumple el diseño |
|---|---|---|
| I. No Invención de Datos | PASS | research.md §4: clasificación con umbral de confianza; fallo o duda → `REVISIÓN MANUAL`, nunca se inventa una clasificación certera. `motivo_clasificacion` en data-model.md da trazabilidad. |
| II. Validación Obligatoria Antes de Archivar | PASS | Ningún endpoint de contracts/api.md permite fijar `estado = PROCESADA`; FR-007/FR-011 mantienen esa transición fuera de esta feature. |
| III. Inmutabilidad de Originales | PASS | research.md §1 y §3: los conectores solo leen (nunca escriben/mueven/eliminan) sobre el buzón; los adjuntos se copian, no se referencian in-place. Validado en quickstart.md Escenario 3. |
| IV. No Sobrescritura de Archivos | PASS | research.md §3: nombre de archivo derivado de `(cuenta_id, message_id, attachment_id)`; si ya existe, se reutiliza la referencia en vez de reescribir. |
| V. Control Humano Explícito | PASS | research.md §5: sincronización solo vía endpoint disparado por humano (`POST /api/mailbox-accounts/{id}/sync`); sin scheduler en el stack de esta feature. |
| VI. Precisión en Estados de Conciliación | N/A | Esta feature no incluye conciliación bancaria (fuera de alcance de spec.md). |
| VII. Uso Acotado de IA de Pago | PASS | research.md §4 documenta el límite de volumen (una llamada por adjunto candidato, acotado por el filtro de formato) y que la Anthropic API solo clasifica, nunca decide archivado. |
| Autenticación y Control de Acceso | PASS | research.md §6: sesión de persona autorizada como prerrequisito de M1; FR-001 y contracts/api.md exigen sesión válida en todos los endpoints. |
| Sistema de Diseño | PASS (aplica a M5) | La pantalla de revisión de candidatos (M5) debe usar Montserrat, paleta blanco+`#0062FF`, tarjetas de radio 12px y la barra de navegación inferior completa (Facturas/Proveedores/Conciliación/Actividad), aunque esta feature solo implemente la pestaña Facturas. |

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
├── main.py                 # Arranque FastAPI
├── models/                 # Entidades de data-model.md (SQLAlchemy Core / dataclasses)
│   ├── mailbox_account.py
│   ├── sync_run.py
│   ├── ingested_email.py
│   └── candidate_document.py
├── services/
│   ├── mailbox/
│   │   ├── base.py         # Interfaz MailboxConnector (research.md §1)
│   │   ├── gmail.py
│   │   ├── imap.py
│   │   └── graph.py
│   ├── sync_service.py     # Orquesta una sincronización manual (FR-004 a FR-009)
│   ├── classification.py   # Filtro de formato + llamada acotada a Anthropic API (research.md §4)
│   └── attachment_store.py # Copia inmutable de adjuntos (research.md §3)
├── api/
│   └── routes/              # Endpoints de contracts/api.md
│       ├── mailbox_accounts.py
│       ├── sync_runs.py
│       └── candidate_documents.py
├── auth/                    # Sesión de persona autorizada (research.md §6)
├── templates/                # UI server-rendered (Jinja2), sistema de diseño (Montserrat, #0062FF)
└── db/
    ├── schema.sql            # Esquema SQLite (M1)
    └── session.py

tests/
├── contract/                 # Contra contracts/api.md
├── integration/               # Escenarios de quickstart.md end-to-end
└── unit/                      # sync_service, classification, attachment_store
```

**Structure Decision**: proyecto único (backend FastAPI que también sirve la UI vía plantillas
Jinja2), sin frontend separado — no hay stack JS declarado en la constitution y el volumen/alcance
de esta feature no lo justifica. Esta estructura es la base para las features futuras (validación,
proveedores, conciliación), que añadirán sus propios módulos bajo `services/` y `api/routes/` sin
reestructurar el proyecto.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No aplica: el Constitution Check no registra ninguna violación (todas las filas son PASS o N/A).
