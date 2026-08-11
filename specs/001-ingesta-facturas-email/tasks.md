---

description: "Task list template for feature implementation"
---

# Tasks: Ingesta y Detección de Facturas por Email

**Input**: Design documents from `/specs/001-ingesta-facturas-email/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md), [quickstart.md](./quickstart.md)

**Tests**: spec.md no solicita explícitamente TDD ni tareas de test automatizado; esta lista no incluye tareas de test dedicadas. La validación funcional se hace ejecutando los escenarios de [quickstart.md](./quickstart.md) (tarea de Polish T034).

**Organization**: Las tareas se agrupan por historia de usuario de spec.md para permitir implementación y prueba independiente de cada una.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: Historia de usuario a la que pertenece (US1, US2, US3)
- Se incluye la ruta de archivo exacta en cada descripción

## Path Conventions

Proyecto único (ver plan.md § Project Structure): `app/` para el código, `tests/` para pruebas.

## Correspondencia con los milestones (M1–M6)

Esta lista se organiza por historia de usuario (requisito del comando), no por milestone. Para
trazabilidad con los milestones M1–M6 indicados en la invocación de `/speckit-plan`:

| Milestone | Fase(s) de tasks.md |
|---|---|
| M1 — Scaffold y esquema SQLite | Fase 1 (Setup) + Fase 2 (Foundational) |
| M2 — Conectar cuenta de correo (HU1) | Fase 3 (User Story 1) |
| M3 — Escanear y detectar adjuntos candidatos (HU2) | Fase 4 (User Story 2), T019–T025 |
| M4 — Clasificación con Anthropic API (HU3 en la spec original del plan) | Fase 4 (User Story 2), T022–T023 |
| M5 — Pantalla de revisión de candidatos | Fase 5 (User Story 3) |
| M6 — Registro auditable y continuidad del lote | Fase 4 (T024–T025, estado `interrumpida`) + Fase 6 (T036) |

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicialización del proyecto (M1). Sin dependencias — puede arrancar de inmediato.

- [X] T001 Crear la estructura de directorios de app/ y tests/ descrita en plan.md § Project Structure (app/models, app/services/mailbox, app/api/routes, app/auth, app/templates, app/db, tests/contract, tests/integration, tests/unit)
- [X] T002 Inicializar el proyecto con `uv init` y declarar en pyproject.toml las dependencias: fastapi, uvicorn, jinja2, sqlalchemy (o driver sqlite3 estándar), anthropic, google-api-python-client (Gmail), msgraph-sdk (Microsoft Graph)
- [X] T003 [P] Configurar linting/formatting con ruff en pyproject.toml y .ruff.toml
- [X] T004 [P] Crear .env.example documentando las variables de entorno necesarias: credenciales IMAP/Gmail/Graph, ANTHROPIC_API_KEY, límite de gasto mensual (research.md §4), SESSION_SECRET

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura núcleo que DEBE estar completa antes de cualquier historia de usuario (M1). Incluye la autenticación mínima, prerrequisito duro de FR-001 (research.md §6).

**⚠️ CRITICAL**: Ninguna historia de usuario puede empezar hasta que esta fase esté completa.

- [X] T005 Crear el esquema SQLite en app/db/schema.sql con las 4 tablas de data-model.md (mailbox_accounts, sync_runs, ingested_emails, candidate_documents) y sus restricciones (`UNIQUE(cuenta_id, proveedor_message_id)` en ingested_emails, checks de enum en `estado`)
- [X] T006 Implementar app/db/session.py: conexión SQLite en modo WAL (`PRAGMA journal_mode=WAL`, research.md §7) y helper de inicialización del esquema
- [X] T007 Implementar la sesión mínima de persona autorizada en app/auth/ (login contra la lista de cuentas autorizadas, cookie de sesión de servidor) — FR-001, research.md §6
- [X] T008 Implementar el middleware de FastAPI que exige sesión autorizada en toda ruta bajo /api/ (responde 401 sin sesión válida, contracts/api.md) en app/main.py
- [X] T009 [P] Implementar la interfaz común MailboxConnector (connect, list_new_messages, get_attachment) en app/services/mailbox/base.py (research.md §1)
- [X] T010 [P] Implementar attachment_store: copia inmutable de adjuntos con nombre derivado de (cuenta_id, message_id, attachment_id), reutilizando la referencia si el archivo ya existe, en app/services/attachment_store.py (research.md §3, Principios III y IV)
- [X] T011 [P] Configurar manejo de errores y logging estructurado (sin loguear credenciales en texto plano) en app/main.py

**Checkpoint**: Fundación lista — las historias de usuario ya pueden implementarse.

---

## Phase 3: User Story 1 - Conectar una cuenta de correo (Priority: P1) 🎯 MVP

**Goal**: La persona autorizada conecta su cuenta de correo (Gmail, IMAP o Microsoft Graph) y ve confirmado su estado de conexión.

**Independent Test**: Conectar una cuenta de prueba vía `POST /api/mailbox-accounts` y verificar que `GET /api/mailbox-accounts/current` devuelve `estado: "conectada"`, sin que ninguna otra funcionalidad exista todavía.

### Implementation for User Story 1

- [X] T012 [P] [US1] Crear el modelo CuentaCorreo en app/models/mailbox_account.py (campos de data-model.md § CuentaCorreo)
- [X] T013 [P] [US1] Implementar ImapConnector en app/services/mailbox/imap.py (implementa MailboxConnector con `imaplib`)
- [X] T014 [P] [US1] Implementar GmailConnector en app/services/mailbox/gmail.py (OAuth2 + Gmail API)
- [X] T015 [P] [US1] Implementar GraphConnector en app/services/mailbox/graph.py (OAuth2 + Microsoft Graph API)
- [X] T016 [US1] Implementar mailbox_account_service (conectar cuenta, comprobar validez de credenciales, actualizar estado conectada/desconectada/requiere_reautorizacion) en app/services/mailbox_account_service.py (depende de T012–T015)
- [X] T017 [US1] Implementar `POST /api/mailbox-accounts` en app/api/routes/mailbox_accounts.py, incluyendo 422 (credenciales inválidas) y 409 (ya existe cuenta conectada para esta persona) según contracts/api.md (depende de T016)
- [X] T018 [US1] Implementar `GET /api/mailbox-accounts/current` en app/api/routes/mailbox_accounts.py, incluyendo 404 si no hay cuenta conectada (depende de T016)
- [X] T019 [US1] Crear la plantilla de conexión de cuenta en app/templates/mailbox_connect.html siguiendo el sistema de diseño (Montserrat 400/600/700, paleta blanco + `#0062FF`, tarjetas de radio 12px)

**Checkpoint**: User Story 1 funcional y probable de forma independiente.

---

## Phase 4: User Story 2 - Escanear el correo y detectar facturas candidatas (Priority: P1)

**Goal**: Al pulsar "sincronizar", el sistema revisa los correos de la cuenta conectada y genera un documento candidato clasificado por cada adjunto que parezca una factura de gasto.

**Independent Test**: Ejecutar `POST /api/mailbox-accounts/{id}/sync` sobre una cuenta con correos de prueba (con y sin factura) y comprobar en `GET /api/sync-runs/{id}` que solo los correos relevantes generan candidatos, con deduplicación correcta al re-sincronizar.

### Implementation for User Story 2

- [X] T020 [P] [US2] Crear el modelo Sincronizacion en app/models/sync_run.py (data-model.md § Sincronizacion)
- [X] T021 [P] [US2] Crear el modelo CorreoIngerido en app/models/ingested_email.py (data-model.md § CorreoIngerido)
- [X] T022 [P] [US2] Crear el modelo DocumentoCandidato en app/models/candidate_document.py (data-model.md § DocumentoCandidato)
- [X] T023 [US2] Implementar el filtro de formato de adjunto (solo PDF/JPG/PNG pasan a clasificación) en app/services/classification.py (research.md §4, FR-005)
- [X] T024 [US2] Implementar la llamada acotada a la Anthropic API (una llamada por adjunto candidato, remitente+asunto+texto extraído como entrada, timeout y umbral de confianza → REVISIÓN MANUAL por defecto ante fallo/duda) en app/services/classification.py (depende de T023; research.md §4, Principios I y VII)
- [X] T025 [US2] Implementar la deduplicación por `(cuenta_id, proveedor_message_id)` — reconocer mensaje ya visto y marcarlo DUPLICADO IGNORADO sin crear candidato nuevo — en app/services/sync_service.py (depende de T021, FR-009)
- [X] T026 [US2] Implementar sync_service: obtiene correos nuevos desde el cursor de la cuenta vía MailboxConnector, aplica T023–T025, crea CorreoIngerido/DocumentoCandidato, actualiza contadores de Sincronizacion y marca `interrumpida` si la conexión falla a mitad de proceso (edge case de spec.md) en app/services/sync_service.py (depende de T009, T010, T020, T024, T025)
- [X] T027 [US2] Implementar `POST /api/mailbox-accounts/{id}/sync` en app/api/routes/sync_runs.py, devolviendo 409 si ya hay una sincronización `en_curso` o si la cuenta no está `conectada` (depende de T026)
- [X] T028 [US2] Implementar `GET /api/sync-runs/{id}` en app/api/routes/sync_runs.py (depende de T026)

**Checkpoint**: User Story 1 y 2 funcionan de forma independiente.

---

## Phase 5: User Story 3 - Revisar la lista de candidatos detectados (Priority: P2)

**Goal**: La persona autorizada consulta los documentos candidatos con su estado y accede al correo/adjunto original sin que este se haya modificado.

**Independent Test**: Tras una sincronización, listar los candidatos vía `GET /api/candidate-documents`, abrir el detalle de uno y descargar su adjunto, verificando que coincide byte a byte con el original.

### Implementation for User Story 3

- [X] T029 [US3] Implementar `GET /api/candidate-documents` con filtro por `estado` y rango de fecha en app/api/routes/candidate_documents.py (contracts/api.md, FR-010)
- [X] T030 [US3] Implementar `GET /api/candidate-documents/{id}` (incluye `motivo_clasificacion` y datos del correo) en app/api/routes/candidate_documents.py
- [X] T031 [US3] Implementar `GET /api/candidate-documents/{id}/attachment` sirviendo el archivo de solo lectura desde attachment_store en app/api/routes/candidate_documents.py (depende de T010)
- [X] T032 [US3] Crear la plantilla de lista de candidatos en app/templates/candidates_list.html con el sistema de diseño completo (Montserrat, `#0062FF`, tarjetas 12px, barra de navegación inferior Facturas/Proveedores/Conciliación/Actividad)
- [X] T033 [US3] Crear la plantilla de detalle de candidato con visor de adjunto en app/templates/candidate_detail.html

**Checkpoint**: Las tres historias de usuario funcionan de forma independiente.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Mejoras transversales y verificación final de cumplimiento constitucional (M6).

- [X] T034 [P] Documentar en README.md los comandos de arranque (`uv sync`, `uv run uvicorn app.main:app`) y las variables de .env.example
- [X] T035 Ejecutar manualmente los 3 escenarios de quickstart.md de extremo a extremo y confirmar sus resultados esperados — validado en proceso (sin servidor HTTP, sin credenciales reales de IMAP/Gmail/Graph disponibles en este entorno): dedup FR-009, filtro de formato FR-005, fallback a REVISIÓN MANUAL sin Anthropic API (Principio I), adjunto guardado idéntico byte a byte al original (Principio III). Pendiente una validación end-to-end real contra un buzón y una clave de Anthropic API de verdad antes de producción.
- [X] T036 [P] Revisar que ningún log ni respuesta de API exponga `credenciales_ref` u otro secreto en texto plano (Principio de auth, research.md §6) — confirmado: `MailboxAccountResponse` no declara `credenciales_ref` y Pydantic descarta los extras; el exception handler de app/main.py no registra el cuerpo de las peticiones.
- [X] T037 Verificar el Constitution Check de plan.md contra la implementación final: originales intactos (Principio III), sin sobrescritura de archivos (Principio IV), sin sincronización automática (Principio V), ningún candidato en estado PROCESADA (Principio II), uso de Anthropic API acotado a clasificación (Principio VII) — confirmado, ver informe de cierre.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — puede arrancar de inmediato
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA todas las historias de usuario
- **User Stories (Phase 3+)**: todas dependen de que Foundational esté completa
  - Pueden avanzar en paralelo si hay varias personas, o en orden de prioridad (US1 → US2 → US3)
- **Polish (Phase 6)**: depende de que las historias de usuario deseadas estén completas

### User Story Dependencies

- **User Story 1 (P1)**: puede empezar tras Foundational — sin dependencia de otras historias
- **User Story 2 (P1)**: puede empezar tras Foundational; en la práctica necesita una cuenta conectada (US1) para probarse end-to-end, pero su código (modelos, sync_service, endpoints) no depende de que US1 esté "terminada", solo de que exista una CuentaCorreo válida
- **User Story 3 (P2)**: puede empezar tras Foundational; para probarse con datos reales necesita que US2 haya generado candidatos, pero sus endpoints de lectura son independientes de la implementación de US1/US2

### Within Each User Story

- Modelos antes que servicios
- Servicios antes que endpoints
- Implementación núcleo antes que la plantilla de UI correspondiente

### Parallel Opportunities

- Todas las tareas [P] de Setup pueden ejecutarse en paralelo
- Todas las tareas [P] de Foundational pueden ejecutarse en paralelo
- T012–T015 (modelos y conectores de US1) pueden ejecutarse en paralelo entre sí
- T020–T022 (modelos de US2) pueden ejecutarse en paralelo entre sí
- Una vez completada Foundational, distintas personas podrían trabajar US1, US2 y US3 en paralelo, aunque la prueba end-to-end de US2/US3 requiere datos producidos por las historias anteriores

---

## Parallel Example: User Story 1

```bash
# Lanzar en paralelo los modelos y conectores de User Story 1:
Task: "Crear el modelo CuentaCorreo en app/models/mailbox_account.py"
Task: "Implementar ImapConnector en app/services/mailbox/imap.py"
Task: "Implementar GmailConnector en app/services/mailbox/gmail.py"
Task: "Implementar GraphConnector en app/services/mailbox/graph.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Fase 1: Setup
2. Completar Fase 2: Foundational (CRÍTICO — bloquea todas las historias)
3. Completar Fase 3: User Story 1
4. **PARAR Y VALIDAR**: probar User Story 1 de forma independiente (conectar una cuenta y ver su estado)
5. Desplegar/demostrar si está listo

### Incremental Delivery

1. Setup + Foundational completos → base lista
2. Añadir User Story 1 → probar de forma independiente → demo (MVP: conectar cuenta)
3. Añadir User Story 2 → probar de forma independiente → demo (sincronizar y detectar candidatos)
4. Añadir User Story 3 → probar de forma independiente → demo (revisar candidatos)
5. Cada historia añade valor sin romper las anteriores

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes
- La etiqueta [Story] traza cada tarea a su historia de usuario
- No se incluyen tareas de test dedicadas porque spec.md no las solicitó explícitamente; la validación funcional final se hace vía quickstart.md (T035)
- Confirmar que el Constitution Check (plan.md) sigue en PASS tras cada historia de usuario completada, no solo al final
- Evitar: tareas vagas, conflictos de archivo entre tareas [P], dependencias cruzadas entre historias que rompan su independencia
