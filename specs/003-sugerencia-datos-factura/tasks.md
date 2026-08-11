---

description: "Task list template for feature implementation"
---

# Tasks: Sugerencia Automática de Datos de Factura

**Input**: Design documents from `/specs/003-sugerencia-datos-factura/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md), [quickstart.md](./quickstart.md)

**Tests**: spec.md no solicita explícitamente TDD ni tareas de test automatizado (mismo criterio que las features 001 y 002); esta lista no incluye tareas de test dedicadas. La validación funcional se hace ejecutando los escenarios de [quickstart.md](./quickstart.md) (tarea de Polish T011).

**Organization**: Esta feature extiende la app ya construida en `specs/001-ingesta-facturas-email/` y `specs/002-validacion-archivado-facturas/` — no crea un proyecto nuevo ni ningún endpoint nuevo.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: Historia de usuario a la que pertenece (US1, US2)
- Se incluye la ruta de archivo exacta en cada descripción

## Path Conventions

Mismo proyecto único que las features 001 y 002 (ver plan.md § Project Structure): `app/` para
el código, `tests/` para pruebas.

## Phase 1: Setup

**Purpose**: Añadir las columnas nuevas antes de tocar ningún código que las use.

- [X] T001 Escribir app/db/migrations/0003_sugerencia_datos_factura.sql: `ALTER TABLE candidate_documents ADD COLUMN` para `sugerido_proveedor_nombre`, `sugerido_fecha_factura`, `sugerido_numero_factura`, `sugerido_total` (todas nullable, sin recrear la tabla — research.md §4, data-model.md) — probado contra una copia de la base de datos real (3 documentos conservados, idempotente)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Generar y guardar las sugerencias en el momento de clasificar — necesario tanto para
User Story 1 como para User Story 2, que solo difieren en cómo se *muestra* el proveedor
sugerido.

**⚠️ CRITICAL**: Ninguna historia de usuario puede empezar hasta que esta fase esté completa.

- [X] T002 Extender CandidateDocument en app/models/candidate_document.py: añadir `sugerido_proveedor_nombre`, `sugerido_fecha_factura`, `sugerido_numero_factura`, `sugerido_total` al dataclass y a `_from_row`, y aceptarlos como parámetros opcionales (por defecto `None`) en `create()` (depende de T001)
- [X] T003 Extender `classify()` en app/services/classification.py: ampliar el prompt para pedir también proveedor/fecha_factura/numero_factura/total sugeridos con una confianza por campo (0.0-1.0), aplicar el umbral de confianza (`0.6`, mismo valor que la clasificación) antes de devolverlos, y devolver un resultado que incluya `estado`, `motivo` y las cuatro sugerencias (cada una `None` si no superó el umbral o no se identificó) — research.md §1-§3
- [X] T004 Actualizar `_process_message` en app/services/sync_service.py para leer las sugerencias devueltas por `classify()` (T003) y pasarlas a `candidate_document_model.create()` (T002) — verificado en proceso: sin API key devuelve sugerido_* en None, umbral de confianza por campo aplicado correctamente, create() persiste y recarga las sugerencias

**Checkpoint**: Fundación lista — los documentos nuevos ya guardan sugerencias; las historias de usuario ya pueden implementarse sobre cómo mostrarlas.

---

## Phase 3: User Story 1 - Ver sugerencias precargadas al revisar un documento (Priority: P1) 🎯 MVP

**Goal**: El formulario de validación de un documento en REVISIÓN MANUAL aparece precargado con
los cuatro campos sugeridos, marcados visualmente como sugerencia, y la persona puede corregirlos
antes de confirmar.

**Independent Test**: Sincronizar un documento con datos identificables, comprobar que `GET
/api/candidate-documents/{id}` devuelve un objeto `sugerencia` con al menos algunos campos, y que
`/facturas/{id}` los muestra precargados (quickstart.md Escenarios 1, 2 y 4).

### Implementation for User Story 1

- [X] T005 [US1] Extender `GET /api/candidate-documents/{id}` en app/api/routes/candidate_documents.py: añadir un campo `sugerencia` (`proveedor_nombre`, `fecha_factura`, `numero_factura`, `total`) a `CandidateDetailResponse`, `null` si el documento no está en REVISIÓN MANUAL o no tiene ningún campo sugerido (FR-008), según contracts/api.md (depende de T002) — verificado en proceso
- [X] T006 [US1] Extender `factura_detail_page` en app/web.py para incluir los campos `sugerido_*` del documento en el contexto pasado a la plantilla, solo cuando `estado == 'REVISIÓN MANUAL'` (depende de T002)
- [X] T007 [US1] Precargar app/templates/candidate_detail.html: los campos de fecha, número y total del formulario de validación toman el valor sugerido como `value` inicial cuando existe, con una marca visual (etiqueta o estilo) que indique "sugerido" — el campo sigue siendo editable y la marca es puramente informativa (depende de T006)

**Checkpoint**: User Story 1 funcional de forma independiente (el proveedor sugerido se muestra como texto simple; el matching contra el catálogo lo añade User Story 2).

---

## Phase 4: User Story 2 - Sugerir un proveedor nuevo cuando no existe en el catálogo (Priority: P2)

**Goal**: Si el proveedor identificado no coincide con ninguno del catálogo, el formulario lo
propone como "proveedor nuevo" en vez de solo mostrar el texto; si coincide con uno activo, lo
preselecciona.

**Independent Test**: Sincronizar un documento cuyo proveedor identificado no exista en el
catálogo, comprobar que `GET /api/candidate-documents/{id}` devuelve
`proveedor_id_coincidente: null`, y que el formulario ofrece "proveedor nuevo" precargado
(quickstart.md Escenario 3).

### Implementation for User Story 2

- [X] T008 [US2] Añadir `proveedor_id_coincidente` a la respuesta de `GET /api/candidate-documents/{id}` en app/api/routes/candidate_documents.py, resolviendo `sugerencia.proveedor_nombre` con `provider_model.get_by_nombre_normalizado()` en el momento de responder (no se persiste, research.md §6), y aplicar la misma resolución en `factura_detail_page` de app/web.py (depende de T005, T006) — verificado en proceso: coincidencia normalizada y sin coincidencia
- [X] T009 [US2] Actualizar app/templates/candidate_detail.html: si hay `proveedor_id_coincidente`, preseleccionar ese proveedor en el `<select>`; si no, dejar el `<select>` en modo "proveedor nuevo" con el nombre sugerido precargado en el campo de texto (depende de T007, T008)

**Checkpoint**: Las dos historias de usuario funcionan de forma independiente.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Verificación final y documentación.

- [X] T010 [P] Actualizar README.md para mencionar la sugerencia automática de datos de factura
- [X] T011 Ejecutar manualmente los 4 escenarios de quickstart.md de extremo a extremo y confirmar sus resultados esperados — validado en proceso (sin servidor HTTP ni llamada real a Anthropic API, no disponible en este entorno): los 4 escenarios pasan, incluida la corrección de un valor sugerido antes de confirmar
- [X] T012 Verificar el Constitution Check de plan.md contra la implementación final: ningún campo con confianza insuficiente se guarda ni se muestra (Principio I), ninguna llamada nueva a la Anthropic API respecto a la ya existente (Principio VII), ningún documento se archiva sin confirmación humana explícita incluso con sugerencias de alta confianza (Principio V) — confirmado, ver informe de cierre

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — puede arrancar de inmediato
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA ambas historias de usuario
- **User Stories (Phase 3-4)**: dependen de que Foundational esté completa
  - US1 puede completarse y entregarse sola (MVP); US2 depende de que US1 ya muestre la
    sugerencia (T007) antes de refinar cómo se resuelve el proveedor (T008-T009)
- **Polish (Phase 5)**: depende de que las historias de usuario deseadas estén completas

### User Story Dependencies

- **User Story 1 (P1)**: depende de Foundational; es el incremento mínimo que ya aporta valor
- **User Story 2 (P2)**: depende de Foundational y de T007 (US1) — refina la misma pantalla que
  US1 ya modificó, en vez de tocar un archivo independiente

### Within Each User Story

- Migración y modelo (Foundational) antes que la lógica de clasificación
- Clasificación (Foundational) antes que la exposición en la API
- API antes que la plantilla que la consume

### Parallel Opportunities

- Ninguna tarea de esta feature es paralelizable de forma significativa: casi todas tocan la
  misma cadena clasificación → API → plantilla, o el mismo archivo que una tarea anterior. Solo
  T010 (Polish) puede ejecutarse en paralelo con T011/T012.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Fase 1: Setup
2. Completar Fase 2: Foundational (CRÍTICO — bloquea todas las historias)
3. Completar Fase 3: User Story 1
4. **PARAR Y VALIDAR**: sincronizar un documento con datos identificables y comprobar que el
   formulario aparece precargado
5. Desplegar/demostrar si está listo

### Incremental Delivery

1. Setup + Foundational completos → base lista
2. Añadir User Story 1 → probar de forma independiente → demo (precarga básica, MVP)
3. Añadir User Story 2 → probar de forma independiente → demo (proveedor nuevo/coincidente)
4. Cada historia añade valor sin romper las anteriores

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes
- La etiqueta [Story] traza cada tarea a su historia de usuario
- No se incluyen tareas de test dedicadas porque spec.md no las solicitó explícitamente; la validación funcional final se hace vía quickstart.md (T011)
- Esta feature no añade ningún endpoint nuevo ni cambia los ya existentes de escritura (`validate`, `reclassify`); solo amplía una respuesta de lectura y precarga un formulario
- Evitar: tareas vagas, conflictos de archivo entre tareas [P], dependencias cruzadas entre historias que rompan su independencia
