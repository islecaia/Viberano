# Research: Lotes con Aprobación Previa y Reanudación

**Fase**: 0 — Outline & Research
**Fecha**: 2026-08-12
**Spec**: [spec.md](./spec.md)

Esta feature extiende la app ya construida en `specs/001-.../002-.../003-.../004-.../005-.../`.
No se introduce ningún stack nuevo.

## 1. Qué se difiere hasta la aprobación: solo la clasificación (coste de IA)

- **Decision**: La fase de "analizar" hace exactamente el mismo trabajo IMAP que la
  sincronización actual (`list_new_messages`, guardar cada adjunto candidato en
  `attachment_store`, crear la fila de `ingested_emails`) — lo único que se difiere es la llamada
  a `classification.classify()` (la única llamada a la Anthropic API) y la creación del
  `candidate_document`. El resumen mostrado antes de aprobar (correos nuevos, correos con
  adjuntos candidatos) se calcula solo mirando el tipo de archivo de cada adjunto
  (`classification.is_supported_format`), sin extraer texto ni clasificar nada.
- **Rationale**: Es el punto exacto donde esta feature aporta valor sobre la sincronización
  actual: dar a la persona autorizada control sobre cuándo se genera el coste de IA (Principio
  VII), sin inventar una fase de "pre-análisis" separada que dupilque el trabajo de lectura del
  buzón. Guardar el adjunto de inmediato (en cuanto se identifica) es coherente con el
  Principio III/IV, que ya rige así desde la feature 001.
- **Alternatives considered**: Diferir también la lectura del buzón (solo contar mensajes vía
  IMAP `SEARCH` sin descargar nada) → descartado: contar "cuántos correos tienen adjuntos
  candidatos" exige mirar el contenido de cada mensaje (`RFC822`) para saber si tiene adjuntos y
  de qué tipo, así que no hay forma de dar ese dato sin ya haber hecho el fetch — una vez hecho,
  guardar el adjunto es prácticamente gratis y evita tener que reconectar al buzón más tarde
  (ver research.md §2).

## 2. Dónde vive el adjunto ya guardado pero aún sin clasificar

- **Decision**: Tabla nueva `pending_attachments` (`correo_id`, `archivo_adjunto_ref`,
  `nombre_archivo_original`, `formato`) — no se amplía `candidate_documents` con un estado
  adicional tipo "PENDIENTE DE CLASIFICAR".
- **Rationale**: `candidate_documents.estado` ya tiene un `CHECK` de 5 valores del que dependen
  las features 002-005 (validación/archivado, sugerencias, conciliación, métricas); añadir un
  sexto estado obligaría a que cada consulta existente sobre esa tabla (listados, métricas,
  conciliación) supiera filtrar explícitamente ese estado "todavía no es un candidato real" para
  no contaminar sus resultados — alto riesgo de romper algo ya construido. Una tabla nueva y
  pequeña, exclusiva de esta feature, mantiene `candidate_documents` exactamente como la conocen
  las demás features: solo contiene documentos ya clasificados.
- **Alternatives considered**: Relajar `motivo_clasificacion` a nullable y usar
  `candidate_documents` directamente con `estado = 'REVISIÓN MANUAL'` provisional →
  descartado por lo anterior, y porque generaría documentos candidato "fantasma" visibles en
  `/facturas` antes de que la persona haya aprobado nada, contradiciendo FR-003 explícitamente
  ("el sistema NO DEBE... guardar ningún documento candidato... hasta que la persona lo apruebe").

## 3. Ampliar `sync_runs.estado`: recreación de tabla, con la lección de la revisión de código

- **Decision**: `sync_runs.estado` pasa de 3 a 4 valores (`pendiente_aprobacion` nuevo). SQLite no
  permite ampliar un `CHECK` existente con `ALTER TABLE`, así que se recrea la tabla (mismo patrón
  que la migración `0002`), y **toda la migración `0005` queda envuelta en `BEGIN TRANSACTION` /
  `COMMIT`** — aplicando directamente la corrección de la revisión de código de esta sesión
  (migraciones `0001`/`0003`/`0004` no estaban envueltas y un fallo a mitad las habría dejado sin
  poder reintentarse).
- **Rationale**: Consistencia con la migración `0002` (mismo problema, misma solución ya probada)
  y con el hallazgo de la revisión de código sobre atomicidad de migraciones.
- **Alternatives considered**: Guardar `pendiente_aprobacion` como una columna booleana aparte
  (`aprobado` `INTEGER`) en vez de un valor de `estado` → descartado: mezclaría dos fuentes de
  verdad sobre el mismo concepto de "en qué punto está este lote", complicando innecesariamente
  cada consulta que hoy solo mira `estado`.

## 4. Aislamiento de errores por correo (FR-009): try/except por correo, no solo alrededor de todo el lote

- **Decision**: La fase de ejecución envuelve el procesamiento de **cada correo** en su propio
  `try/except`: si falla, se marca `ingested_emails.estado_procesamiento = 'FALLIDO'` con
  `motivo_fallo`, se incrementa `correos_procesados` igualmente (se intentó), y el bucle continúa
  con el siguiente correo. El `try/except` amplio que envuelve **todo** el bucle (introducido en
  la revisión de código de esta sesión para que `sync_run` nunca quede atascada `en_curso` ante un
  fallo inesperado) se conserva como red de seguridad para fallos verdaderamente sistémicos (p. ej.
  la base de datos deja de responder) — pero ya no es la primera línea de defensa para un fallo de
  un único correo.
- **Rationale**: Es exactamente lo que pide FR-009/Acceptance Scenario de User Story 3: un fallo
  puntual no debe impedir que el resto del lote se guarde. El catch-all sigue siendo necesario
  para no reintroducir el bug que se corrigió antes (`sync_run` atascada para siempre).
- **Alternatives considered**: Seguir abortando todo el lote ante cualquier fallo (comportamiento
  actual) → descartado explícitamente por spec.md, User Story 3.

## 5. Un único endpoint de ejecución para aprobar, reanudar y reintentar

- **Decision**: `POST /api/mailbox-accounts/{id}/sync/{sync_run_id}/execute` es el único endpoint
  que dispara la fase de ejecución. Procesa todos los `ingested_emails` de ese lote cuyo
  `estado_procesamiento` sea `PENDIENTE` o `FALLIDO`. Se puede llamar cuando `sync_runs.estado` es
  `pendiente_aprobacion` (primera aprobación), `interrumpida` (reanudar tras un fallo sistémico) o
  `completada` (reintentar los correos que quedaron `FALLIDO`).
- **Rationale**: Las tres historias de usuario (aprobar, reanudar, reintentar) son, vistas desde
  el backend, la misma operación: "procesa lo que quede pendiente o fallido de este lote". Un
  único endpoint reduce la superficie de API y el código a mantener; la interfaz puede mostrar
  botones con etiquetas distintas ("Aprobar y procesar" / "Reintentar fallidos") según el estado
  visible del lote, sin que eso implique una ruta distinta en el backend.
- **Alternatives considered**: Tres endpoints separados (`/approve`, `/resume`, `/retry-failed`) →
  descartado por duplicar la misma lógica de selección de correos pendientes tres veces sin
  ninguna diferencia de comportamiento real entre ellos.

## 6. Cuándo avanza el cursor de la cuenta

- **Decision**: `mailbox_accounts.ultima_sincronizacion_cursor` se actualiza al terminar la fase
  de **análisis** (no la de ejecución), con la fecha/hora en que se hizo el fetch a IMAP.
- **Rationale**: Es el punto real hasta el que se ha leído el buzón — coherente con FR-008 (no
  duplicar correos ya analizados) sin depender de si su clasificación tuvo éxito o no. Un correo
  cuyo procesamiento falla sigue siendo reintentable localmente (ya está guardado en
  `ingested_emails` + `pending_attachments`) sin necesitar volver a leer el buzón.
- **Alternatives considered**: Actualizar el cursor solo al completar la ejecución →
  descartado: dejaría una ventana en la que, si la persona tarda en aprobar el lote, un nuevo
  intento de análisis volvería a traer los mismos correos ya identificados, obligando a
  `find_existing` a filtrarlos de nuevo en vez de que el cursor ya lo evite de raíz.

## Resumen de resolución de Assumptions de spec.md

| Assumption en spec.md | Traducción técnica |
|---|---|
| No existe "rechazar" un lote en v1 | Sin endpoint de rechazo; un lote `pendiente_aprobacion` simplemente espera a `execute` (research.md §5) |
| Un lote pendiente/en curso por cuenta a la vez | Índice único parcial ampliado a `estado IN ('pendiente_aprobacion', 'en_curso')` |
| El resumen no requiere clasificar los adjuntos | research.md §1 |
| El reintento reutiliza el mismo lote | research.md §5 — mismo `sync_run`, mismo endpoint |
| Sin límite de reintentos | No se añade ningún contador de intentos al esquema |

No quedan `NEEDS CLARIFICATION` pendientes en el Technical Context de plan.md.
