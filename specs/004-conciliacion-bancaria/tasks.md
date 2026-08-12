---

description: "Task list template for feature implementation"
---

# Tasks: Conciliación Bancaria

**Input**: Design documents from `/specs/004-conciliacion-bancaria/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md), [quickstart.md](./quickstart.md)

**Tests**: spec.md no solicita explícitamente TDD ni tareas de test automatizado (mismo criterio que las features 001-003); esta lista no incluye tareas de test dedicadas. La validación funcional se hace ejecutando los escenarios de [quickstart.md](./quickstart.md) (tarea de Polish T018).

**Organization**: Esta feature extiende la app ya construida en las features 001-003 — no crea un proyecto nuevo.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: Historia de usuario a la que pertenece (US1, US2, US3)
- Se incluye la ruta de archivo exacta en cada descripción

## Path Conventions

Mismo proyecto único que las features anteriores (ver plan.md § Project Structure): `app/` para
el código, `tests/` para pruebas.

## Phase 1: Setup

**Purpose**: Añadir el esquema nuevo antes de tocar ningún código que lo use.

- [X] T001 Escribir app/db/migrations/0004_conciliacion_bancaria.sql: crear `bank_statements`, `bank_movements`, `reconciliation_candidates`, y añadir a `candidate_documents` las columnas `estado_conciliacion` (nullable, `CHECK` con los 4 valores de data-model.md) y `movimiento_bancario_id` (nullable, FK) vía `ADD COLUMN` — sin recrear ninguna tabla (data-model.md) — probado contra una copia de la base de datos real (5 documentos conservados, idempotente)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelos base que necesitan las tres historias de usuario.

**⚠️ CRITICAL**: Ninguna historia de usuario puede empezar hasta que esta fase esté completa.

- [X] T002 [P] Crear el modelo BankStatement en app/models/bank_statement.py: `create(fecha_inicio, fecha_fin, aportado_por, total_movimientos)`, `get_by_id(id)` (data-model.md § BankStatement)
- [X] T003 [P] Crear el modelo BankMovement en app/models/bank_movement.py: `create_bulk(extracto_id, movimientos)`, `get_by_id(id)`, `find_candidatos(importe, fecha_factura, ventana_dias)` (research.md §3, excluye movimientos ya vinculados) (depende de T002)
- [X] T004 Extender CandidateDocument en app/models/candidate_document.py: añadir `estado_conciliacion` y `movimiento_bancario_id` al dataclass y a `_from_row`, y las funciones `mark_conciliada(documento_id, movimiento_id)`, `mark_no_encontrada(documento_id)`, `mark_pendiente_revision(documento_id)`, todas exigiendo `estado = 'PROCESADA'` y `estado_conciliacion` actual `NULL` (data-model.md, research.md §4) — verificado en proceso: dedup FR-009, MovimientoYaVinculadoError, ConciliacionYaResueltaError, ciclo pendiente→resuelto
- [X] T005 [P] Crear el modelo ReconciliationCandidate en app/models/reconciliation_candidate.py: `create_many(documento_id, movimiento_ids)`, `list_for_documento(documento_id)`, `clear_for_documento(documento_id)` (data-model.md § ReconciliationCandidate)

**Checkpoint**: Fundación lista — las historias de usuario ya pueden implementarse.

---

## Phase 3: User Story 1 - Aportar un extracto y ver qué facturas tienen respaldo de pago (Priority: P1) 🎯 MVP

**Goal**: La persona autorizada aporta un extracto CSV y ve qué facturas `PROCESADA` del periodo
quedan conciliadas y cuáles "no encontradas en el extracto".

**Independent Test**: `POST /api/reconciliations` con un CSV donde un movimiento coincide
claramente con una factura y otro no coincide con ninguna; comprobar que la primera queda
`CONCILIADA` y la segunda `NO ENCONTRADA EN EXTRACTO` (quickstart.md Escenarios 1 y 2).

### Implementation for User Story 1

- [X] T006 [US1] Implementar app/services/reconciliation_service.py: parsear y validar el CSV (cabecera `fecha,importe,concepto`, rechazo todo-o-nada si falta algo, research.md §2), inferir `fecha_inicio`/`fecha_fin` del contenido (research.md §1), y para cada factura `PROCESADA` del periodo sin `estado_conciliacion` buscar candidatos con `BankMovement.find_candidatos` y aplicar `mark_conciliada`/`mark_no_encontrada`/`mark_pendiente_revision` según haya 1/0/N candidatos (research.md §3) (depende de T003, T004, T005) — verificado en proceso
- [X] T007 [US1] Implementar `POST /api/reconciliations` en app/api/routes/reconciliations.py: recibe el CSV por `multipart/form-data`, devuelve 422 si es inválido (sin crear nada) o 201 con el resumen (conciliadas/no_encontradas/pendientes_revision), según contracts/api.md (depende de T006)
- [X] T008 [US1] Implementar `GET /api/reconciliations/{id}` en app/api/routes/reconciliations.py con el detalle completo (data-model.md, contracts/api.md) (depende de T007) — nota: durante la implementación se detectó que hacía falta rastrear qué extracto produjo cada estado_conciliacion (columna `conciliado_con_extracto_id`, añadida a T001/T004 retroactivamente antes de aplicarse a ninguna base de datos real)
- [X] T009 [US1] Extender `GET /api/candidate-documents/{id}` en app/api/routes/candidate_documents.py para incluir `estado_conciliacion` y `movimiento_conciliado` cuando existan (depende de T004) — verificado en proceso: conciliada con movimiento, no encontrada nunca "impagada"
- [X] T010 [US1] Crear app/templates/reconciliation.html: formulario para subir el CSV y, tras conciliar, resumen con recuento de conciliadas/no encontradas/pendientes (depende de T007, T008)
- [X] T011 [US1] Sustituir la ruta placeholder `GET /conciliacion` en app/web.py (hoy usa placeholder.html) por la pantalla real basada en reconciliation.html (depende de T010) — incluye también `GET /conciliacion/{id}` para el detalle

**Checkpoint**: User Story 1 funcional de forma independiente (MVP).

---

## Phase 4: User Story 2 - Resolver manualmente una factura con varias coincidencias posibles (Priority: P2)

**Goal**: La persona autorizada elige el movimiento correcto (o descarta todos) cuando una
factura queda `PENDIENTE REVISIÓN CONCILIACIÓN`.

**Independent Test**: Con una factura que tiene dos movimientos candidatos, `POST
/api/candidate-documents/{id}/reconcile` con uno de ellos y comprobar que pasa a `CONCILIADA`
(quickstart.md Escenario 3).

### Implementation for User Story 2

- [X] T012 [US2] Implementar `POST /api/candidate-documents/{id}/reconcile` en app/api/routes/candidate_documents.py: valida que el documento esté `PENDIENTE REVISIÓN CONCILIACIÓN` y que `movimiento_id` (si no es `null`) sea uno de sus candidatos guardados, llama a `mark_conciliada`/`mark_no_encontrada` y limpia los candidatos con `ReconciliationCandidate.clear_for_documento`, según contracts/api.md (depende de T004, T005) — verificado con script en proceso: (a) elegir candidato válido → CONCILIADA y candidatos limpiados, (b) descartar todos (`movimiento_id: null`) → NO ENCONTRADA EN EXTRACTO, (c) `movimiento_id` fuera de los candidatos → 422, (d) documento no pendiente de conciliación → 422; ruff limpio
- [X] T013 [US2] Extender app/templates/candidate_detail.html con una tarjeta de "Conciliación bancaria": muestra `estado_conciliacion` y, si está `PENDIENTE REVISIÓN CONCILIACIÓN`, lista los movimientos candidatos con un botón por cada uno ("Elegir este movimiento") y un botón "Ninguno es correcto" (depende de T009, T012) — implementado junto con el contexto correspondiente en app/web.py (`factura_detail_page`: `estado_conciliacion`, `movimiento_conciliado`, `conciliacion_candidatos`); ruff limpio

**Checkpoint**: User Story 1 y 2 funcionan de forma independiente.

---

## Phase 5: User Story 3 - Ver los movimientos de gasto sin factura asociada (Priority: P2)

**Goal**: La persona autorizada ve, para un extracto procesado, los cargos sin ninguna factura
vinculada.

**Independent Test**: `GET /api/reconciliations/{id}` sobre un extracto con un cargo sin factura
correspondiente y un ingreso; comprobar que el cargo aparece en
`movimientos_pendientes_de_justificar` y el ingreso no (quickstart.md Escenario 4).

### Implementation for User Story 3

- [X] T014 [US3] Implementar `find_pendientes_de_justificar(extracto_id)` en app/models/bank_movement.py: movimientos con `importe < 0` (cargos) del extracto sin ningún `candidate_documents.movimiento_bancario_id` que los referencie (FR-007/FR-008, research.md §5) (depende de T003) — ya implementado durante T008 (la respuesta combinada de GET /api/reconciliations/{id} lo requería); reverificado presente en app/models/bank_movement.py
- [X] T015 [US3] Incluir `movimientos_pendientes_de_justificar` en la respuesta de `GET /api/reconciliations/{id}` (depende de T008, T014) — ya implementado durante T008; reverificado presente en app/api/routes/reconciliations.py
- [X] T016 [US3] Mostrar esa lista en app/templates/reconciliation.html (depende de T010, T015) — ya implementado durante T010; reverificado presente en app/templates/reconciliation.html

**Checkpoint**: Las tres historias de usuario funcionan de forma independiente.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verificación final y documentación.

- [X] T017 [P] Actualizar README.md para mencionar la conciliación bancaria — añadida entrada de specs/004-conciliacion-bancaria/ a la lista de features
- [X] T018 Ejecutar manualmente los 5 escenarios de quickstart.md de extremo a extremo y confirmar sus resultados esperados — verificados los 5 con script en proceso; se precisó la redacción del Escenario 3 en quickstart.md (el candidato se limpia para la factura resuelta, no desaparece de otras facturas pendientes — que reciben 409 si intentan usar un movimiento ya vinculado, por el índice único)
- [X] T019 Verificar el Constitution Check de plan.md contra la implementación final: ninguna coincidencia ambigua se resuelve automáticamente (Principio I), ninguna factura se marca como impagada (Principio VI), la conciliación solo se ejecuta por acción explícita (Principio V), sin ningún uso de IA (Principio VII) — verificado: `bank_movement.py` copia los datos del CSV sin inventar nada y las ambigüedades van a PENDIENTE REVISIÓN CONCILIACIÓN sin elegir por adivinanza (Principio I); el CHECK constraint de `estado_conciliacion` en la migración 0004 solo admite CONCILIADA/NO ENCONTRADA EN EXTRACTO/PENDIENTE REVISIÓN CONCILIACIÓN — "impagada" es estructuralmente imposible (Principio VI); `procesar_extracto`/`reconcile_candidate` solo se ejecutan por POST explícito de la persona autorizada, sin scheduling en ningún fichero nuevo de esta feature (Principio V); `reconciliation_service.py` no importa ni llama a ninguna API de IA — matching puramente determinista (Principio VII)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — puede arrancar de inmediato
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA todas las historias de usuario
- **User Stories (Phase 3-5)**: dependen de que Foundational esté completa
  - US1 es el incremento mínimo (MVP)
  - US2 depende de que existan facturas `PENDIENTE REVISIÓN CONCILIACIÓN`, producidas por US1 —
    aun así su código (T012) no depende de que la UI de US1 (T010/T011) esté terminada
  - US3 depende solo de Foundational a nivel de código, aunque para probarla con datos reales
    conviene haber ejecutado ya una conciliación (US1)
- **Polish (Phase 6)**: depende de que las historias de usuario deseadas estén completas

### User Story Dependencies

- **User Story 1 (P1)**: depende de Foundational; es el MVP
- **User Story 2 (P2)**: depende de Foundational; su endpoint (T012) es independiente de la UI de
  US1, pero T013 comparte archivo (`candidate_detail.html`) con las features 002 y 003
- **User Story 3 (P2)**: depende de Foundational (T003/T014); su endpoint se apoya en T008 (US1)
  para exponerse, pero la consulta en sí (T014) no depende del código de US1 o US2

### Within Each User Story

- Modelos y migraciones (Foundational) antes que el servicio de conciliación
- Servicio antes que endpoints
- Endpoints antes que las plantillas que los consumen

### Parallel Opportunities

- T002, T003 y T005 (modelos de Foundational) pueden ejecutarse en paralelo entre sí
- T017 (Polish) puede ejecutarse en paralelo con T018/T019

---

## Parallel Example: Foundational

```bash
# Lanzar en paralelo los modelos de la Fase 2:
Task: "Crear el modelo BankStatement en app/models/bank_statement.py"
Task: "Crear el modelo BankMovement en app/models/bank_movement.py"
Task: "Crear el modelo ReconciliationCandidate en app/models/reconciliation_candidate.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Fase 1: Setup
2. Completar Fase 2: Foundational (CRÍTICO — bloquea todas las historias)
3. Completar Fase 3: User Story 1
4. **PARAR Y VALIDAR**: aportar un extracto de prueba y comprobar el resumen de conciliación
5. Desplegar/demostrar si está listo

### Incremental Delivery

1. Setup + Foundational completos → base lista
2. Añadir User Story 1 → probar de forma independiente → demo (MVP: conciliar automáticamente)
3. Añadir User Story 2 → probar de forma independiente → demo (resolver ambigüedad a mano)
4. Añadir User Story 3 → probar de forma independiente → demo (ver gastos sin factura)
5. Cada historia añade valor sin romper las anteriores

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes
- La etiqueta [Story] traza cada tarea a su historia de usuario
- No se incluyen tareas de test dedicadas porque spec.md no las solicitó explícitamente; la validación funcional final se hace vía quickstart.md (T018)
- Esta feature no toca la ingesta, la validación/archivado ni las sugerencias de las features anteriores — solo lee documentos `PROCESADA` ya existentes
- Evitar: tareas vagas, conflictos de archivo entre tareas [P], dependencias cruzadas entre historias que rompan su independencia
