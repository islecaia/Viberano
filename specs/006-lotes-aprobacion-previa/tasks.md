---

description: "Task list template for feature implementation"
---

# Tasks: Lotes con Aprobación Previa y Reanudación

**Input**: Design documents from `/specs/006-lotes-aprobacion-previa/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md), [quickstart.md](./quickstart.md)

**Tests**: spec.md no solicita explícitamente TDD ni tareas de test automatizado (mismo criterio que las features 001-005); esta lista no incluye tareas de test dedicadas. La validación funcional se hace ejecutando los escenarios de [quickstart.md](./quickstart.md) (tarea de Polish T016).

**Organization**: Esta feature extiende la app ya construida en las features 001-005 — no crea un proyecto nuevo. Reemplaza el flujo síncrono actual de `POST .../sync` (feature 001) por dos fases explícitas: analizar y ejecutar (research.md).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: Historia de usuario a la que pertenece (US1, US2, US3)
- Se incluye la ruta de archivo exacta en cada descripción

## Path Conventions

Mismo proyecto único que las features anteriores (ver plan.md § Project Structure): `app/` para
el código, `tests/` para pruebas.

## Phase 1: Setup

**Purpose**: Añadir el esquema nuevo antes de tocar ningún código que lo use.

- [X] T001 Escribir app/db/migrations/0005_lotes_aprobacion_previa.sql: recrear `sync_runs` con el `CHECK` de `estado` ampliado (+ `pendiente_aprobacion`) y las columnas nuevas `correos_nuevos_detectados`/`correos_con_adjuntos_candidatos`; sustituir el índice único parcial de "una sincronización activa por cuenta" para cubrir `estado IN ('pendiente_aprobacion', 'en_curso')`; `ALTER TABLE ingested_emails ADD COLUMN` para `estado_procesamiento` (`DEFAULT 'PROCESADO'`, con su `CHECK`) y `motivo_fallo`; crear la tabla nueva `pending_attachments` — todo envuelto en `BEGIN TRANSACTION`/`COMMIT` (research.md §3, lección de la revisión de código sobre atomicidad de migraciones) — probado contra una copia de la base de datos real (6 correos, 11 sincronizaciones conservados, `PRAGMA foreign_key_check` vacío); nota añadida durante la implementación: a diferencia de la migración 0002, `sync_runs` ya tiene tablas hijas (`ingested_emails`), así que hubo que envolver el DROP+RENAME con `PRAGMA foreign_keys = OFF/ON` fuera de la transacción (SQLite no permite alternar esa pragma dentro de un `BEGIN`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelos base que necesitan las tres historias de usuario.

**⚠️ CRITICAL**: Ninguna historia de usuario puede empezar hasta que esta fase esté completa.

- [X] T002 [P] Extender SyncRun en app/models/sync_run.py: añadir `correos_nuevos_detectados`/`correos_con_adjuntos_candidatos` al dataclass y a `_from_row`; `create_analisis(cuenta_id, iniciada_por)` crea el `sync_run` en `pendiente_aprobacion`; `guardar_resumen(sync_id, correos_nuevos, correos_con_adjuntos)`; `marcar_completada(sync_id)`/`marcar_interrumpida(sync_id)` (equivalentes al `finish()` actual, ahora sin fijar `estado` a mano); `get_pendiente_o_en_curso(cuenta_id)` sustituye a `get_en_curso()` para cubrir ambos estados (data-model.md § Sincronizacion/Lote) (depende de T001) — verificado en proceso: índice único impide un segundo lote activo por cuenta, todas las transiciones de estado
- [X] T003 [P] Extender IngestedEmail en app/models/ingested_email.py: añadir `estado_procesamiento`/`motivo_fallo` al dataclass y a `_from_row`; `create()` acepta `estado_procesamiento` (por defecto `'PENDIENTE'` para correos nuevos); `marcar_procesado(correo_id)`, `marcar_fallido(correo_id, motivo)`; `list_pendientes_o_fallidos(sync_run_id)` (data-model.md § CorreoIngerido) (depende de T001) — verificado en proceso; añadido también `get_by_id()` y `list_fallidos()` (necesarios para T012/T013)
- [X] T004 [P] Crear el modelo PendingAttachment en app/models/pending_attachment.py: `create(correo_id, archivo_adjunto_ref, nombre_archivo_original, formato)`, `list_for_correo(correo_id)`, `delete_for_correo(correo_id)` (data-model.md § AdjuntoPendiente) (depende de T001) — verificado en proceso

**Checkpoint**: Fundación lista — las historias de usuario ya pueden implementarse.

---

## Phase 3: User Story 1 - Aprobar un lote antes de procesarlo (Priority: P1) 🎯 MVP

**Goal**: Al sincronizar, la persona autorizada ve un resumen del lote (correos nuevos, correos
con adjuntos candidatos) antes de que se cree ningún documento candidato, y debe aprobarlo
explícitamente para que se procese.

**Independent Test**: Sincronizar una cuenta con correos nuevos, comprobar que el lote queda
`pendiente_aprobacion` con su resumen y sin documentos candidato nuevos; aprobar el lote y
comprobar que los documentos candidato aparecen (quickstart.md Escenarios 1 y 2).

### Implementation for User Story 1

- [X] T005 [US1] Añadir `analizar_lote(cuenta_id, persona_autorizada)` en app/services/sync_service.py: valida que no exista ya un lote `pendiente_aprobacion`/`en_curso` para la cuenta (FR-005), crea el `sync_run` (T002), abre el conector y llama a `list_new_messages`, y por cada mensaje no duplicado (mismo criterio `find_existing` que hoy) crea el `ingested_email` (T003) y guarda cada adjunto candidato en `attachment_store` + `pending_attachment` (T004) — sin clasificar ni crear `candidate_documents` todavía; al terminar, actualiza `mailbox_accounts.ultima_sincronizacion_cursor` (research.md §6) y guarda el resumen calculado (depende de T002, T003, T004) — verificado en proceso: 3 correos nuevos, 2 con adjunto, 0 candidatos creados, cursor actualizado
- [X] T006 [US1] Añadir `ejecutar_lote(sync_run_id, persona_autorizada)` en app/services/sync_service.py: valida que el lote pertenezca a la cuenta de la persona y esté en un estado ejecutable (`pendiente_aprobacion`, `interrumpida` o `completada`); para cada `ingested_email` de ese lote en `PENDIENTE` (US2/US3 lo ampliarán a `FALLIDO`): clasifica sus `pending_attachments` (`classification.classify`), crea los `candidate_documents`, borra los `pending_attachments` consumidos y marca el correo `PROCESADO`; al terminar marca el `sync_run` `completada` (`fecha_fin`); conserva el `except Exception` amplio de la revisión de código anterior como red de seguridad para fallos sistémicos, marcando `interrumpida` y repropagando (depende de T005) — nota: durante la implementación se construyó directamente con `list_pendientes_o_fallidos()` (incluye `FALLIDO`) y try/except por correo, adelantando el trabajo de T010/T012 (US2/US3); `pending_attachment.delete()` se añadió por adjunto individual, no por correo completo, para que un correo con varios adjuntos que falla a mitad no duplique los ya convertidos al reintentar; verificado en proceso
- [X] T007 [US1] Actualizar app/api/routes/sync_runs.py: `POST /api/mailbox-accounts/{id}/sync` pasa a llamar a `analizar_lote()` (ya no ejecuta la clasificación); nuevo `POST /api/mailbox-accounts/{id}/sync/{sync_run_id}/execute` llama a `ejecutar_lote()`, `404` si el lote no pertenece a la cuenta, `422` si no queda nada `PENDIENTE`/`FALLIDO`; `SyncRunResponse` ampliado con `correos_nuevos_detectados`/`correos_con_adjuntos_candidatos` (contracts/api.md) (depende de T006) — excepciones separadas `LoteNoEncontradoError`(404)/`NadaQueEjecutarError`(422); verificado en proceso
- [X] T008 [US1] Ampliar `GET /api/sync-runs/{id}` en app/api/routes/sync_runs.py con los mismos campos nuevos que T007 (contracts/api.md) (depende de T007) — implementado junto con T007 vía `_to_response()` compartido; verificado en proceso
- [X] T009 [US1] Actualizar app/templates/candidates_list.html y `facturas_page()` en app/web.py: si la cuenta tiene un lote `pendiente_aprobacion`, mostrar su resumen y un botón "Aprobar y procesar" (llama a `POST .../execute`); el botón "Sincronizar" ahora dispara el análisis en vez de recargar directamente (depende de T008) — añadido `sync_run_model.get_ultimo()` (lote más reciente en cualquier estado, lo reutilizarán T011/T014); verificado en proceso: tarjeta y resumen visibles en /facturas

**Checkpoint**: User Story 1 funcional de forma independiente (aprobar un lote crea los documentos candidato; reanudar y reintentar fallidos los añaden las historias siguientes).

---

## Phase 4: User Story 2 - Reanudar sin repetir trabajo ya hecho (Priority: P2)

**Goal**: Si la ejecución de un lote aprobado se interrumpe, reanudarla continúa desde el último
correo completado sin volver a procesarlo ni duplicarlo.

**Independent Test**: Interrumpir la ejecución de un lote a mitad (simulando un fallo sistémico)
y reanudarla, comprobando que los correos ya guardados no se reprocesan (quickstart.md, mismo
mecanismo que el Escenario 4 pero disparado por una interrupción en vez de un fallo de correo).

### Implementation for User Story 2

- [X] T010 [US2] Verificar en app/services/sync_service.py que `ejecutar_lote()` (T006), al reanudarse sobre un `sync_run` `interrumpida`, solo procesa los `ingested_emails` todavía `PENDIENTE` de ese lote (los ya `PROCESADO` se excluyen por la propia consulta de T003) — sin cambios de código si T006 ya filtra correctamente por `estado_procesamiento`; si no, corregir el filtro (depende de T006) — sin cambios de código necesarios (T006 ya lo hacía); verificado en proceso simulando un fallo sistémico a mitad del lote: el correo ya procesado no se repite al reanudar, los candidatos finales no se duplican
- [X] T011 [US2] Actualizar app/templates/candidates_list.html: mostrar un botón "Reanudar" cuando el lote esté `interrumpida`, llamando al mismo `POST .../execute` que T009 (depende de T009, T010) — reutiliza el mismo `#lote-action-button`/JS que T009; verificado en proceso

**Checkpoint**: User Story 1 y 2 funcionan de forma independiente.

---

## Phase 5: User Story 3 - Ver y reintentar los correos que fallaron (Priority: P3)

**Goal**: Un fallo al procesar un correo concreto no bloquea el resto del lote; los correos
fallidos quedan visibles con su motivo y se pueden reintentar sin repetir los ya guardados.

**Independent Test**: Simular que el procesamiento de un correo de un lote de varios falla,
comprobar que los demás se guardan igualmente y que el fallido aparece en `correos_fallidos`;
reintentarlo y comprobar que pasa a `PROCESADO` (quickstart.md Escenarios 3 y 4).

### Implementation for User Story 3

- [X] T012 [US3] Refinar `ejecutar_lote()` en app/services/sync_service.py: envolver el procesamiento de cada `ingested_email` en su propio `try`/`except` — al fallar, marca ese correo `FALLIDO` con `motivo_fallo` (T003) y continúa con el siguiente en vez de abortar el lote entero (FR-009, research.md §4); ampliar la consulta de correos a procesar para incluir también los `FALLIDO` (permite reintentar sobre un lote `completada`) (depende de T006) — ya implementado en T006; verificado en proceso con un fallo real de un correo concreto (clasificación): el lote termina `completada`, los demás correos se procesan, y el reintento posterior corrige el fallido sin duplicar los demás
- [X] T013 [US3] Exponer `correos_fallidos` (id, remitente, asunto, motivo_fallo) en la respuesta de `POST .../execute` y `GET /api/sync-runs/{id}` en app/api/routes/sync_runs.py (contracts/api.md) (depende de T012, T008) — ya implementado en T007/T008 vía `_to_response()`; verificado en proceso
- [X] T014 [US3] Actualizar app/templates/candidates_list.html: listar los correos fallidos de un lote `completada` con su motivo, y un botón "Reintentar fallidos" que llama a `POST .../execute` (depende de T011, T013) — verificado en proceso: asunto, motivo_fallo y el botón aparecen en /facturas

**Checkpoint**: Las tres historias de usuario funcionan de forma independiente.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verificación final y documentación.

- [X] T015 [P] Actualizar README.md para mencionar el flujo de analizar/aprobar/reintentar lotes — añadida entrada de specs/006-lotes-aprobacion-previa/ a la lista de features
- [X] T016 Ejecutar manualmente los 5 escenarios de quickstart.md de extremo a extremo y confirmar sus resultados esperados — verificados los 5 con script en proceso: resumen sin candidatos, aprobar crea candidatos, fallo de un correo no bloquea el resto (completada, no interrumpida), reintento corrige el fallido sin duplicar, 409 al analizar con un lote pendiente
- [X] T017 Verificar el Constitution Check de plan.md contra la implementación final: ningún documento candidato se crea sin aprobación explícita (Principio V, FR-003), la clasificación por IA no se invoca hasta la aprobación (Principio VII), un fallo de correo no bloquea el resto del lote (FR-009) — confirmado: `classification.classify()`/`extract_text()` solo se llaman desde `_procesar_correo_pendiente()`, exclusivamente dentro de `ejecutar_lote()` (nunca en `analizar_lote()`); `analizar_lote()`/`ejecutar_lote()` solo se disparan por `POST` explícito de la persona autorizada, sin scheduling en ningún fichero nuevo de esta feature

---

## Phase 7: Addendum — No crear lote cuando no hay nada que revisar (FR-013)

**Purpose**: FR-013, añadido tras la implementación inicial a petición explícita del usuario — si
el análisis no encuentra ningún correo con adjunto candidato, no debe quedar ningún registro de
lote, y la cuenta debe quedar libre de inmediato para una nueva sincronización.

- [X] T018 [US1] Refactorizar `analizar_lote()` en app/services/sync_service.py: separar el análisis (lectura de IMAP + cálculo en memoria, función nueva `_analizar_mensajes()`) de la persistencia (`_persistir_correos_analizados()`, nueva); solo crear el `sync_run` y guardar correos/adjuntos si `correos_con_adjuntos_candidatos > 0`; devolver `None` en caso contrario; el cursor de la cuenta avanza siempre, haya o no lote (FR-013, research.md) — verificado en proceso: 0 filas en `sync_runs`/`ingested_emails` cuando no hay adjuntos candidatos, cursor avanzado, cuenta libre para una nueva sincronización inmediata (sin `SincronizacionEnCursoError`)
- [X] T019 [US1] Actualizar app/api/routes/sync_runs.py: `POST .../sync` devuelve ahora `AnalisisResponse { lote: SyncRunResponse | null }`; capturar `MailboxConnectionError` (ya no se traga dentro de `analizar_lote()` al no existir un `sync_run` que marcar `interrumpida`) y mapearlo a `502 Bad Gateway` (depende de T018) — verificado en proceso: `{"lote": null}` cuando no hay nada que revisar, `502` ante un fallo de conexión
- [X] T020 [US1] Actualizar app/templates/candidates_list.html: el botón "Sincronizar" interpreta `data.lote` de la respuesta — si es `null`, muestra "No se han encontrado correos nuevos con posible factura" sin recargar; si trae un lote, recarga como antes (depende de T019) — verificado manualmente contra el nuevo formato de respuesta

**Checkpoint**: un análisis sin nada que aprobar no deja ningún rastro en `sync_runs` y no bloquea la siguiente sincronización.

---

## Phase 8: Hotfix — Lote sin correos pendientes/fallidos quedaba atascado sin salida

**Purpose**: Bug real observado en producción tras T018-T020: un `sync_run` `pendiente_aprobacion`
con 0 correos (dato heredado de antes de FR-013, o cualquier condición de carrera futura) no
tenía ningún correo `PENDIENTE`/`FALLIDO` que ejecutar — `POST .../execute` respondía `422` y la
única forma de desbloquear la cuenta era editar la base de datos a mano.

- [X] T021 [US1] Corregir `ejecutar_lote()` en app/services/sync_service.py: cuando no queda ningún correo `PENDIENTE`/`FALLIDO`, en vez de lanzar `NadaQueEjecutarError` (eliminada, era el único uso), cerrar el lote como `completada` si no lo estaba ya y devolver su estado actual — cubre tanto un lote sin ningún correo desde el principio como un reintento repetido (doble clic, dos pestañas) sobre un lote ya resuelto; actualizar app/api/routes/sync_runs.py (eliminar el `except NadaQueEjecutarError`/import) y contracts/api.md (ya no hay `422` en este endpoint) — verificado en proceso; aplicado además directamente contra el lote 13 atascado en la base de datos real de desarrollo (quedó `completada`, cuenta libre de inmediato)

**Checkpoint**: `POST .../execute` nunca deja un lote sin ninguna acción posible desde la UI.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — puede arrancar de inmediato
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA las tres historias de usuario
- **User Stories (Phase 3-5)**: dependen de que Foundational esté completa
  - US1 puede completarse y entregarse sola (MVP); US2 y US3 amplían la misma función
    `ejecutar_lote()` que US1 ya creó, en vez de tocar archivos independientes
- **Polish (Phase 6)**: depende de que las historias de usuario deseadas estén completas

### User Story Dependencies

- **User Story 1 (P1)**: depende de Foundational; es el incremento mínimo que ya aporta valor
  (analizar + aprobar)
- **User Story 2 (P2)**: depende de Foundational y de T006 (US1) — reanudar es, en la práctica,
  volver a llamar a `ejecutar_lote()` sobre un lote `interrumpida`
- **User Story 3 (P3)**: depende de Foundational y de T006 (US1) — refina la misma función para
  aislar errores por correo y permite reintentar sobre un lote `completada`

### Within Each User Story

- Modelos (Foundational) antes que `analizar_lote()`/`ejecutar_lote()`
- `analizar_lote()` antes que `ejecutar_lote()` (T006 depende de T005 solo por orden lógico de
  lectura del archivo; no hay dependencia de datos entre ambas)
- Servicio antes que los endpoints
- Endpoints antes que la plantilla que los consume

### Parallel Opportunities

- T002, T003, T004 (Foundational) son archivos distintos y pueden ejecutarse en paralelo.
- Dentro de cada historia, casi todas las tareas dependen de la anterior en la misma cadena
  servicio → endpoint → plantilla. Solo T015 (Polish) puede ejecutarse en paralelo con T016/T017.

---

## Parallel Example: Foundational

```bash
Task: "Extender SyncRun en app/models/sync_run.py"
Task: "Extender IngestedEmail en app/models/ingested_email.py"
Task: "Crear el modelo PendingAttachment en app/models/pending_attachment.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (CRITICAL — bloquea las tres historias)
3. Completar Phase 3: User Story 1
4. **STOP and VALIDATE**: probar User Story 1 de forma independiente (analizar → ver resumen →
   aprobar → ver los documentos candidato)
5. Deploy/demo si está listo

### Incremental Delivery

1. Setup + Foundational → esquema y modelos listos
2. Añadir User Story 1 → probar de forma independiente → Deploy/Demo (MVP)
3. Añadir User Story 2 → probar de forma independiente → Deploy/Demo
4. Añadir User Story 3 → probar de forma independiente → Deploy/Demo
5. Cada historia añade valor sin romper la anterior

---

## Notes

- [P] tasks = archivos distintos, sin dependencias
- La etiqueta [Story] vincula cada tarea con su historia de usuario para trazabilidad
- Cada historia de usuario debe poder completarse y probarse de forma independiente
- Confirmar cada tarea con verificación en proceso (mismo criterio que las features 001-005,
  dado que no se solicitó TDD)
- Detenerse en cada checkpoint para validar la historia de forma independiente
