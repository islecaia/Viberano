---

description: "Task list template for feature implementation"
---

# Tasks: Validación y Archivado con Revisión Humana

**Input**: Design documents from `/specs/002-validacion-archivado-facturas/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md), [quickstart.md](./quickstart.md)

**Tests**: spec.md no solicita explícitamente TDD ni tareas de test automatizado (mismo criterio que `specs/001-ingesta-facturas-email/tasks.md`); esta lista no incluye tareas de test dedicadas. La validación funcional se hace ejecutando los escenarios de [quickstart.md](./quickstart.md) (tarea de Polish T017).

**Organization**: Las tareas se agrupan por historia de usuario de spec.md. Esta feature extiende la app ya construida en `specs/001-ingesta-facturas-email/` — no crea un proyecto nuevo.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: Historia de usuario a la que pertenece (US1, US2, US3)
- Se incluye la ruta de archivo exacta en cada descripción

## Path Conventions

Mismo proyecto único que la feature 001 (ver plan.md § Project Structure): `app/` para el
código, `tests/` para pruebas.

## Phase 1: Setup

**Purpose**: Preparar la carpeta de migraciones sin tocar todavía el esquema nuevo.

- [X] T001 Crear app/db/migrations/ y mover el contenido actual de app/db/schema.sql a app/db/migrations/0001_initial.sql sin cambios (research.md §1); eliminar app/db/schema.sql una vez migrado

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Esquema y modelos base que necesitan tanto User Story 1 como User Story 3
(Provider y los campos nuevos de CandidateDocument). Nada de las historias de usuario puede
implementarse hasta que esta fase esté completa.

**⚠️ CRITICAL**: Ninguna historia de usuario puede empezar hasta que esta fase esté completa.

- [X] T002 Escribir app/db/migrations/0002_validacion_archivado.sql: crear tabla `providers`, recrear `candidate_documents` con el CHECK de `estado` ampliado a incluir `PROCESADA` y las columnas nuevas (`proveedor_id`, `fecha_factura`, `numero_factura`, `total`, `es_nota_credito`, `validado_por`, `fecha_validacion`), y crear el índice único parcial `ux_candidate_documents_factura_procesada` (research.md §2-§4, data-model.md)
- [X] T003 Implementar el runner de migraciones en app/db/session.py: tabla `schema_migrations(version, applied_at)`, aplica en orden los `.sql` de app/db/migrations/ no registrados todavía, cada uno en su propia transacción (research.md §1); actualizar `init_db()` para usarlo en vez de ejecutar schema.sql directamente — probado contra una copia de la base de datos real (3 documentos existentes conservados, idempotente)
- [X] T004 [P] Crear el modelo Provider en app/models/provider.py: `create(nombre, identificador_fiscal)`, `get_by_nombre_normalizado(nombre)`, `get_by_id(id)`, `list_all(activo=None)`, `set_activo(id, activo)` (data-model.md § Proveedor, research.md §5)
- [X] T005 [P] Extender CandidateDocument en app/models/candidate_document.py con los campos nuevos de data-model.md y dos funciones: `mark_procesada(id, proveedor_id, fecha_factura, numero_factura, total, es_nota_credito, validado_por)` y `reclassify(id, estado)` (solo `NO ES FACTURA`/`FACTURA DE VENTA`), ambas comprobando primero que el documento sigue en `REVISIÓN MANUAL` — verificado en proceso: normalización de nombre, mark_procesada, DocumentoNoEnRevisionError, ArchivadoDuplicadoError y reclassify funcionan correctamente

**Checkpoint**: Fundación lista — las historias de usuario ya pueden implementarse.

---

## Phase 3: User Story 1 - Validar y archivar un documento candidato (Priority: P1) 🎯 MVP

**Goal**: La persona autorizada introduce/confirma proveedor, fecha, número y total de un
documento en REVISIÓN MANUAL y confirma su archivado, pasando el documento a PROCESADA.

**Independent Test**: `POST /api/candidate-documents/{id}/validate` con un proveedor activo y
los cuatro campos sobre un documento en REVISIÓN MANUAL, y comprobar que pasa a PROCESADA con
esos datos y `validado_por`/`fecha_validacion` rellenos (quickstart.md Escenario 1).

### Implementation for User Story 1

- [X] T006 [US1] Implementar app/services/validation_service.py: valida los cuatro campos (fecha válida, número no vacío, total numérico y solo negativo si `es_nota_credito`), resuelve el proveedor por `proveedor_id` o lo crea a partir de `proveedor_nombre_nuevo`, comprueba que esté activo, comprueba la colisión del índice único de data-model.md con un mensaje claro antes de escribir, y si todo es correcto llama a `CandidateDocument.mark_procesada(...)` (depende de T004, T005)
- [X] T007 [US1] Implementar `POST /api/candidate-documents/{id}/validate` en app/api/routes/candidate_documents.py devolviendo 422 (campos inválidos), 409 (proveedor inactivo, incluyendo su `proveedor_id` en la respuesta), 409 (documento ya no está en REVISIÓN MANUAL) o 409 (colisión con otro documento PROCESADA), según contracts/api.md (depende de T006)
- [X] T008 [US1] Extender `GET /api/candidate-documents/{id}` en app/api/routes/candidate_documents.py para incluir proveedor, fecha_factura, numero_factura, total, es_nota_credito, validado_por y fecha_validacion cuando el documento ya está validado (depende de T005)
- [X] T009 [US1] Extender app/templates/candidate_detail.html con el formulario de validación (selector de proveedor existente + campo "proveedor nuevo", fecha, número, total, checkbox de nota de crédito, botón "Validar y archivar"), visible solo cuando `estado == 'REVISIÓN MANUAL'`, y mostrando los cuatro campos ya guardados cuando el documento está PROCESADA (depende de T007, T008) — verificado en proceso: proveedor al vuelo, GET refleja datos, proveedor inactivo → 409, total inválido → 422, colisión → 409 con documento_id

**Checkpoint**: User Story 1 funcional (puede probarse creando el proveedor al vuelo con `proveedor_nombre_nuevo`, sin depender de que User Story 2 esté terminada).

---

## Phase 4: User Story 2 - Mantener un catálogo mínimo de proveedores activos (Priority: P1)

**Goal**: La persona autorizada añade proveedores y los marca activos/inactivos.

**Independent Test**: Crear un proveedor, comprobar que aparece activo en `GET /api/providers`,
desactivarlo con `PATCH /api/providers/{id}` y comprobar que ya no puede usarse para validar un
documento nuevo (quickstart.md Escenario 2).

### Implementation for User Story 2

- [X] T010 [P] [US2] Implementar `POST /api/providers` y `GET /api/providers` en app/api/routes/providers.py, devolviendo 409 si ya existe un proveedor con ese nombre normalizado, según contracts/api.md (depende de T004)
- [X] T011 [US2] Implementar `PATCH /api/providers/{id}` en app/api/routes/providers.py, devolviendo 404 si no existe (depende de T010)
- [X] T012 [US2] Crear app/templates/providers.html: lista de proveedores con su estado, formulario para añadir uno nuevo, y un control para activar/desactivar cada uno (depende de T010, T011)
- [X] T013 [US2] Sustituir la ruta placeholder `GET /proveedores` en app/web.py (que hoy usa placeholder.html) por la pantalla real basada en providers.html (depende de T012) — verificado en proceso: crear, nombre duplicado → 409, listar, activar/desactivar y filtro por activo

**Checkpoint**: User Story 1 y 2 funcionan de forma independiente; juntas dan el flujo completo de validación con proveedores gestionados desde la interfaz.

---

## Phase 5: User Story 3 - Corregir una clasificación automática equivocada (Priority: P2)

**Goal**: La persona autorizada marca un documento en REVISIÓN MANUAL como NO ES FACTURA o
FACTURA DE VENTA sin pasar por los cuatro campos de validación.

**Independent Test**: `POST /api/candidate-documents/{id}/reclassify` con `{"estado": "NO ES FACTURA"}` sobre un documento en REVISIÓN MANUAL, comprobar que cambia de estado sin pedir proveedor/fecha/número/total, y que un segundo intento sobre el mismo documento devuelve 409 (quickstart.md Escenario 3).

### Implementation for User Story 3

- [X] T014 [US3] Implementar `POST /api/candidate-documents/{id}/reclassify` en app/api/routes/candidate_documents.py, devolviendo 422 si `estado` no es `NO ES FACTURA`/`FACTURA DE VENTA` o 409 si el documento ya no está en REVISIÓN MANUAL, según contracts/api.md (depende de T005)
- [X] T015 [US3] Añadir a app/templates/candidate_detail.html los botones "Marcar NO ES FACTURA" y "Marcar FACTURA DE VENTA", visibles solo cuando `estado == 'REVISIÓN MANUAL'`, junto al formulario de validación de User Story 1 (depende de T014, T009) — verificado en proceso: reclasificar, rechazo de re-reclasificar (409) y estado no permitido (422)

**Checkpoint**: Las tres historias de usuario funcionan de forma independiente.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verificación final y documentación.

- [X] T016 [P] Actualizar README.md para mencionar el catálogo de proveedores y el flujo de validación/archivado
- [X] T017 Ejecutar manualmente los 4 escenarios de quickstart.md de extremo a extremo y confirmar sus resultados esperados — validado en proceso (sin servidor HTTP): los 4 escenarios pasan, incluida la reactivación de proveedor tras bloqueo
- [X] T018 [P] Revisar que los logs no registren más datos fiscales de los necesarios (mismo criterio que T036 de specs/001-ingesta-facturas-email/tasks.md, aplicado ahora a proveedor/fecha/número/total) — confirmado: los `logger.warning` de esta feature no existen (los errores se propagan como HTTPException); el único log que toca `exc.detail` (app/main.py) solo expone ids internos y mensajes genéricos, nunca los valores de fecha/número/total introducidos
- [X] T019 Verificar el Constitution Check de plan.md contra la implementación final: ningún campo se completa automáticamente (Principio I), ningún documento llega a PROCESADA sin los cuatro campos y proveedor activo (Principio II), ninguna colisión de archivado sobrescribe un documento existente (Principio IV), archivado solo por confirmación explícita (Principio V), sin ningún uso nuevo de IA (Principio VII) — confirmado, ver informe de cierre

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — puede arrancar de inmediato
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA todas las historias de usuario
- **User Stories (Phase 3+)**: todas dependen de que Foundational esté completa
  - US1 y US2 pueden avanzar en paralelo si hay varias personas (ambas dependen solo de Foundational, no la una de la otra a nivel de código — aunque para probar US1 con datos reales conviene tener ya un proveedor, que US1 puede crear al vuelo)
  - US3 puede avanzar en paralelo a US1/US2, salvo por T015, que toca el mismo archivo que T009 (candidate_detail.html)
- **Polish (Phase 6)**: depende de que las historias de usuario deseadas estén completas

### User Story Dependencies

- **User Story 1 (P1)**: depende de Foundational (Provider y CandidateDocument extendidos); no depende de que User Story 2 esté "terminada" porque puede crear el proveedor al vuelo (`proveedor_nombre_nuevo`)
- **User Story 2 (P1)**: depende de Foundational (Provider); no depende de User Story 1
- **User Story 3 (P2)**: depende de Foundational (CandidateDocument extendido); comparte archivo de plantilla con User Story 1 (T015 después de T009)

### Within Each User Story

- Modelos y migraciones (Foundational) antes que servicios
- Servicios antes que endpoints
- Endpoints antes que la plantilla que los consume

### Parallel Opportunities

- T004 y T005 (modelos de Foundational) pueden ejecutarse en paralelo entre sí
- T010 (US2) puede ejecutarse en paralelo con toda la Fase 3 (US1), ya que tocan archivos distintos
- T016 y T018 (Polish) pueden ejecutarse en paralelo

---

## Parallel Example: Foundational

```bash
# Lanzar en paralelo los dos modelos de la Fase 2:
Task: "Crear el modelo Provider en app/models/provider.py"
Task: "Extender CandidateDocument en app/models/candidate_document.py con los campos nuevos"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Fase 1: Setup
2. Completar Fase 2: Foundational (CRÍTICO — bloquea todas las historias)
3. Completar Fase 3: User Story 1 (creando proveedores al vuelo con `proveedor_nombre_nuevo`)
4. **PARAR Y VALIDAR**: validar y archivar un documento de principio a fin
5. Desplegar/demostrar si está listo

### Incremental Delivery

1. Setup + Foundational completos → base lista
2. Añadir User Story 1 → probar de forma independiente → demo (validar y archivar, MVP)
3. Añadir User Story 2 → probar de forma independiente → demo (gestionar proveedores desde la UI en vez de solo al vuelo)
4. Añadir User Story 3 → probar de forma independiente → demo (reclasificar sin validar)
5. Cada historia añade valor sin romper las anteriores

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes
- La etiqueta [Story] traza cada tarea a su historia de usuario
- No se incluyen tareas de test dedicadas porque spec.md no las solicitó explícitamente; la validación funcional final se hace vía quickstart.md (T017)
- Esta feature modifica el esquema de una base de datos que ya tiene datos reales de la feature 001 — T002/T003 deben probarse contra una copia de esa base de datos antes de aplicarse en el entorno de desarrollo del usuario, para confirmar que la migración conserva los datos existentes
- Evitar: tareas vagas, conflictos de archivo entre tareas [P], dependencias cruzadas entre historias que rompan su independencia
