---

description: "Task list template for feature implementation"
---

# Tasks: Volumen Mensual de Facturas

**Input**: Design documents from `/specs/005-volumen-mensual-facturas/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md), [quickstart.md](./quickstart.md)

**Tests**: spec.md no solicita explícitamente TDD ni tareas de test automatizado (mismo criterio que las features 001-004); esta lista no incluye tareas de test dedicadas. La validación funcional se hace ejecutando los escenarios de [quickstart.md](./quickstart.md) (tarea de Polish T011).

**Organization**: Esta feature extiende la app ya construida en las features 001-004 — no crea un proyecto nuevo. Es de solo lectura: no hay migración de esquema (data-model.md).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: Historia de usuario a la que pertenece (US1, US2)
- Se incluye la ruta de archivo exacta en cada descripción

## Path Conventions

Mismo proyecto único que las features anteriores (ver plan.md § Project Structure): `app/` para
el código, `tests/` para pruebas.

## Phase 1: Setup

**Purpose**: Inicialización del proyecto.

No aplica ninguna tarea: esta feature no añade ninguna dependencia nueva ni requiere migración de
esquema (research.md §1, data-model.md) — se agrega directamente sobre columnas ya existentes
desde las features 001 y 002.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Consulta base del recuento mensual, necesaria tanto para User Story 1 como para User
Story 2 (que solo añade la media y el flag de mes parcial sobre el mismo recuento).

**⚠️ CRITICAL**: Ninguna historia de usuario puede empezar hasta que esta fase esté completa.

- [X] T001 [P] Añadir `count_procesada_por_mes(fecha_inicio: str, fecha_fin: str) -> list[dict]` en app/models/candidate_document.py: agrupa por `strftime('%Y-%m', fecha_factura)` filtrando `estado = 'PROCESADA'` y `fecha_factura` dentro de `[fecha_inicio, fecha_fin]` (FR-002, FR-003, FR-004; data-model.md, research.md §1) — verificado en proceso: agrupa correctamente, excluye estados distintos de PROCESADA
- [X] T002 Crear app/services/metrics_service.py: `volumen_mensual(desde: str, hasta: str) -> dict` que genera **todos** los meses del rango `desde`..`hasta` (formato `YYYY-MM`) combinando con `count_procesada_por_mes` (T001), incluyendo los meses sin ninguna factura con `total: 0` en vez de omitirlos (FR-005) (depende de T001) — verificado en proceso: mes intermedio sin facturas aparece con total 0, rango cruza de año correctamente; ruff limpio

**Checkpoint**: Fundación lista — el recuento mensual completo está disponible; las historias de usuario ya pueden implementarse.

---

## Phase 3: User Story 1 - Ver el recuento mensual de facturas procesadas (Priority: P1) 🎯 MVP

**Goal**: La persona autorizada puede consultar, para un periodo, cuántas facturas `PROCESADA`
tiene archivadas cada mes, incluidos los meses en 0.

**Independent Test**: Archivar facturas `PROCESADA` con fechas de emisión repartidas en varios
meses (y alguna en otro estado), consultar el endpoint y comprobar que el recuento de cada mes
coincide exactamente con las `PROCESADA` de ese mes, sin omitir meses vacíos (quickstart.md
Escenarios 1 y 2).

### Implementation for User Story 1

- [X] T003 [US1] Crear app/api/routes/metrics.py: modelos Pydantic `MesRecuento` (`mes`, `total`) y `VolumenMensualResponse` (`desde`, `hasta`, `meses: list[MesRecuento]`), endpoint `GET /api/metrics/volumen-mensual` con query params opcionales `desde`/`hasta` (`YYYY-MM`); si se omiten, usa el periodo por defecto de 12 meses rodantes (research.md §3); `422` si el formato no es válido o `desde` es posterior a `hasta` (contracts/api.md) (depende de T002) — validación de periodo centralizada en `metrics_service.resolver_periodo()` para reutilizarla también desde web.py; verificado en proceso: periodo explícito, periodo por defecto (12 meses hasta el mes en curso), 422 en mes inválido y en desde > hasta
- [X] T004 [US1] Registrar `metrics_router` en app/api/routes/__init__.py (depende de T003)
- [X] T005 [US1] Crear app/templates/activity.html: pantalla que muestra la lista de meses del periodo con su recuento (incluidos los de `total: 0`) y un formulario de periodo (`<input type="month">`), siguiendo el sistema de diseño (Montserrat, tarjetas de 12px) (depende de T004) — renderizado server-side (mismo patrón que candidates_list.html/reconciliation.html), sin fetch al cargar
- [X] T006 [US1] Actualizar `actividad_page()` en app/web.py: renderizar `activity.html` en vez del placeholder, resolviendo el periodo con `metrics_service.resolver_periodo()` y llamando a `metrics_service.volumen_mensual()` (depende de T005) — `_placeholder_page()` y `placeholder.html` eliminados por quedar sin ningún uso (las 4 pestañas ya tienen feature propia); verificado en proceso: `/actividad?desde=2026-05&hasta=2026-07` renderiza los 3 meses pedidos

**Checkpoint**: User Story 1 funcional de forma independiente (recuento mensual visible; la media se añade en User Story 2).

---

## Phase 4: User Story 2 - Ver la media mensual, distinguiendo meses completos de meses parciales (Priority: P2)

**Goal**: La persona autorizada ve, junto al recuento, la media del periodo, con el mes en curso
(y el primer mes de conexión de la cuenta, si fue parcial) claramente distinguidos de los meses
completos.

**Independent Test**: Consultar un periodo que incluya el mes en curso y comprobar que se
devuelven dos medias etiquetadas de forma distinguible: `media_meses_completos` (sin el mes en
curso) y `media_con_mes_parcial` (con él) (quickstart.md Escenarios 3 y 4).

### Implementation for User Story 2

- [X] T007 [US2] Extender `volumen_mensual()` en app/services/metrics_service.py: añadir el flag `completo` por mes — `false` si es el mes en curso o si es el mes de conexión de la cuenta (`mailbox_accounts.fecha_conexion`) con conexión posterior al día 1 de ese mes, `true` en cualquier otro caso (research.md §2) — y calcular `media_meses_completos` (solo meses con `completo: true`, `null` si no hay ninguno) y `media_con_mes_parcial` (todos los meses del periodo) (data-model.md § Media del Periodo) (depende de T002) — verificado en proceso: mes de conexión a mitad de mes y mes en curso marcados `completo=False`, media_meses_completos excluye ambos, medias coinciden cuando el periodo no tiene ningún mes parcial (Acceptance Scenario 1)
- [X] T008 [US2] Extender app/api/routes/metrics.py: añadir `completo: bool` a `MesRecuento` y `media_meses_completos: float | None` / `media_con_mes_parcial: float | None` a `VolumenMensualResponse`, según contracts/api.md (depende de T003, T007) — resuelve `fecha_conexion` vía `mailbox_account_model.get_for_persona()`; verificado en proceso
- [X] T009 [US2] Actualizar app/templates/activity.html: mostrar las dos medias etiquetadas de forma distinguible cuando el periodo tenga algún mes parcial (una sola media si no lo tiene), y marcar visualmente en la lista qué mes es parcial (depende de T005, T008) — verificado en proceso: badge "mes parcial" y ambas medias etiquetadas presentes en el HTML renderizado

**Checkpoint**: Las dos historias de usuario funcionan de forma independiente.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Verificación final y documentación.

- [X] T010 [P] Actualizar README.md para mencionar el volumen mensual de facturas — añadida entrada de specs/005-volumen-mensual-facturas/ a la lista de features
- [X] T011 Ejecutar manualmente los 5 escenarios de quickstart.md de extremo a extremo y confirmar sus resultados esperados — verificados los 5 con script en proceso: recuento solo PROCESADA, mes intermedio en 0 sin omitirse, mes en curso parcial con medias distintas, mes de conexión a mitad de mes también parcial, periodo inválido → 422
- [X] T012 Verificar el Constitution Check de plan.md contra la implementación final: ningún mes se muestra con un valor inventado o estimado (Principio I), la consulta solo se ejecuta por acción explícita de la persona autorizada, sin cálculo programado (Principio V) — confirmado: `count_procesada_por_mes`/`volumen_mensual` solo cuentan filas reales (el 0 de un mes sin facturas es un conteo real, no una estimación); sin `schedule`/`cron`/`BackgroundTasks` en ningún fichero nuevo de esta feature

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin tareas — no aplica
- **Foundational (Phase 2)**: sin dependencias de Setup — BLOQUEA ambas historias de usuario
- **User Stories (Phase 3-4)**: dependen de que Foundational esté completa
  - US1 puede completarse y entregarse sola (MVP); US2 extiende el mismo servicio y la misma
    plantilla que US1 ya creó, en vez de tocar archivos independientes
- **Polish (Phase 5)**: depende de que las historias de usuario deseadas estén completas

### User Story Dependencies

- **User Story 1 (P1)**: depende de Foundational; es el incremento mínimo que ya aporta valor
  (recuento mensual, sin media)
- **User Story 2 (P2)**: depende de Foundational y de T003/T005 (US1) — añade la media y el flag
  de mes parcial sobre el mismo endpoint y la misma plantilla que US1 ya creó

### Within Each User Story

- Modelo (Foundational) antes que el servicio
- Servicio antes que el endpoint
- Endpoint antes que la plantilla que lo consume
- Plantilla antes que la ruta de página que la renderiza

### Parallel Opportunities

- T001 (Foundational) puede ejecutarse en paralelo si hubiera otras tareas de modelo independientes, aunque aquí no las hay.
- Dentro de cada historia, casi todas las tareas dependen de la anterior en la misma cadena modelo → servicio → endpoint → plantilla. Solo T010 (Polish) puede ejecutarse en paralelo con T011/T012.

---

## Parallel Example: Foundational

```bash
# T001 es la única tarea marcada [P] de esta feature (sin otras tareas de modelo independientes con las que paralelizarse en este caso).
Task: "Añadir count_procesada_por_mes en app/models/candidate_document.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 2: Foundational (sin Phase 1, que no aplica)
2. Completar Phase 3: User Story 1
3. **STOP and VALIDATE**: probar User Story 1 de forma independiente (recuento mensual visible en
   la pestaña Actividad)
4. Deploy/demo si está listo

### Incremental Delivery

1. Foundational → recuento mensual disponible internamente
2. Añadir User Story 1 → probar de forma independiente → Deploy/Demo (MVP)
3. Añadir User Story 2 → probar de forma independiente → Deploy/Demo
4. Cada historia añade valor sin romper la anterior

---

## Notes

- [P] tasks = archivos distintos, sin dependencias
- La etiqueta [Story] vincula cada tarea con su historia de usuario para trazabilidad
- Cada historia de usuario debe poder completarse y probarse de forma independiente
- Confirmar cada tarea con verificación en proceso (mismo criterio que las features 001-004,
  dado que no se solicitó TDD)
- Detenerse en cada checkpoint para validar la historia de forma independiente
