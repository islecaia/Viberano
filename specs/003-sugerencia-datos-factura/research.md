# Research: Sugerencia Automática de Datos de Factura

**Fase**: 0 — Outline & Research
**Fecha**: 2026-08-11
**Spec**: [spec.md](./spec.md)

Esta feature extiende la app ya construida en `specs/001-ingesta-facturas-email/` (clasificación)
y `specs/002-validacion-archivado-facturas/` (validación). No se introduce ningún stack nuevo.

## 1. Una sola llamada a Anthropic API, no dos (Principio VII)

- **Decision**: Ampliar el *mismo* prompt y la misma llamada que ya hace
  `app/services/classification.py::classify()` (feature 001) para que, además de `estado` y
  `motivo`, devuelva también los cuatro campos sugeridos (`proveedor`, `fecha_factura`,
  `numero_factura`, `total`) con su confianza individual, en un único objeto JSON de respuesta.
  No se añade una segunda llamada a la API.
- **Rationale**: El Principio VII de la constitution acota el uso de la Anthropic API a "una
  llamada por adjunto candidato" (research.md §4 de la feature 001). Añadir una llamada aparte
  para generar sugerencias duplicaría el coste y rompería ese límite ya establecido.
- **Alternatives considered**: Llamada adicional solo para los documentos que quedan en REVISIÓN
  MANUAL → descartada porque en el momento de clasificar todavía no sabemos con certeza en qué
  estado quedará el documento antes de tener la respuesta, y porque duplica coste sin necesidad
  cuando ya se dispone del texto extraído en esa misma llamada.

## 2. Cuándo se genera la sugerencia: una vez, al clasificar (no en cada visita a la pantalla)

- **Decision**: Las sugerencias se calculan y se guardan en el momento de la clasificación
  (dentro de `sync_service._process_message`, feature 001), no cada vez que se abre el detalle
  del documento.
- **Rationale**: Evita llamadas repetidas a la API cada vez que alguien abre la pantalla
  (Principio VII), y hace que el comportamiento sea determinista: la sugerencia que ve la persona
  es siempre la misma mientras el documento siga en REVISIÓN MANUAL.
- **Alternatives considered**: Generar la sugerencia bajo demanda al abrir `GET
  /api/candidate-documents/{id}` → descartada por lo anterior (coste y determinismo).

## 3. Umbral de confianza y qué se guarda

- **Decision**: El umbral de confianza se aplica una sola vez, en el momento de generar la
  sugerencia: un campo por debajo del umbral (`0.6`, mismo valor que `_CONFIDENCE_THRESHOLD` de
  classification.py) simplemente no se guarda (columna a `NULL`) en vez de guardarse junto a un
  valor de confianza que habría que volver a evaluar después.
- **Rationale**: Simplifica el modelo de datos (no hace falta guardar ni volver a interpretar un
  número de confianza en la capa de presentación) y hace FR-003 trivial de cumplir: si la columna
  está vacía, el campo no se sugiere.
- **Alternatives considered**: Guardar también la confianza numérica de cada campo → descartado
  por añadir una complejidad (¿qué umbral usa la UI? ¿puede cambiar sin releer el documento?) que
  spec.md no pide y que no aporta valor adicional sobre decidirlo una vez en el origen.

## 4. Migración de esquema: solo columnas nuevas, sin recrear tablas

- **Decision**: `app/db/migrations/0003_sugerencia_datos_factura.sql` añade cuatro columnas
  nullable a `candidate_documents` (`sugerido_proveedor_nombre`, `sugerido_fecha_factura`,
  `sugerido_numero_factura`, `sugerido_total`) con `ALTER TABLE ... ADD COLUMN`. A diferencia de
  la migración 0002 (specs/002-validacion-archivado-facturas/research.md §2), esta vez no hace
  falta recrear la tabla: SQLite sí permite añadir columnas nullable sin tocar ningún `CHECK`
  existente.
- **Rationale**: Es la operación más simple posible para el cambio necesario; recrear la tabla
  sería una complejidad innecesaria cuando `ADD COLUMN` basta.
- **Alternatives considered**: Ninguna — es el caso simple que la migración 0002 ya identificó
  como la alternativa cuando no hace falta tocar un `CHECK`.

## 5. Sin reevaluación retroactiva

- **Decision**: Los documentos que ya estaban en REVISIÓN MANUAL antes de que se aplique la
  migración 0003 quedan con las cuatro columnas nuevas a `NULL` — el formulario de validación las
  trata exactamente igual que un documento sin sugerencia (spec.md, Assumptions).
- **Rationale**: Coincide con la decisión ya tomada en spec.md; no se necesita ningún trabajo
  adicional porque es el comportamiento por defecto de columnas nuevas en filas existentes.
- **Alternatives considered**: Backfill que reprocese documentos antiguos → explícitamente fuera
  de alcance en spec.md.

## 6. Resolución del proveedor sugerido: reutilizar la lógica ya existente

- **Decision**: Cuando se muestra el formulario, si `sugerido_proveedor_nombre` no es nulo, se
  busca con `provider_model.get_by_nombre_normalizado()` (ya existente, feature 002). Si hay
  coincidencia, se preselecciona ese proveedor; si no, se precarga el campo "proveedor nuevo" con
  el nombre sugerido (User Story 2). No se guarda un `proveedor_id` sugerido en la base de datos:
  se resuelve en el momento de mostrar la pantalla, para reflejar siempre el catálogo actual (un
  proveedor pudo darse de alta después de generarse la sugerencia).
- **Rationale**: Reutiliza al 100% la función de normalización de nombre ya construida y probada
  en la feature 002 (research.md §5 de esa feature); no hace falta ninguna lógica de coincidencia
  nueva.
- **Alternatives considered**: Guardar un `proveedor_id` sugerido en el momento de clasificar →
  descartado porque el catálogo de proveedores puede cambiar entre que se genera la sugerencia y
  se revisa el documento, y resolver por nombre en el momento de mostrarlo es más correcto.

## 7. Contrato de API: sin endpoints nuevos

- **Decision**: No se añade ningún endpoint. `GET /api/candidate-documents/{id}` (feature 001,
  ampliado por la feature 002) se amplía una vez más para incluir los campos sugeridos cuando
  existen; `POST /api/candidate-documents/{id}/validate` (feature 002) no cambia — la persona
  sigue enviando los mismos cuatro campos, ahora simplemente precargados en el formulario antes
  de enviarlos.
- **Rationale**: Esta feature es una precarga de UI sobre un flujo que ya existe; no introduce
  ninguna acción nueva del usuario, solo reduce cuánto tiene que escribir.
- **Alternatives considered**: Endpoint separado `GET .../suggestions` → descartado por
  innecesario; añadir los campos al detalle ya existente es más simple y evita una llamada extra
  desde el cliente.

## Resumen de resolución de Assumptions de spec.md

| Assumption en spec.md | Traducción técnica |
|---|---|
| Umbral de confianza es detalle técnico | `0.6`, igual que el umbral de clasificación ya existente (research.md §3). |
| Sugerencia generada una vez, al clasificar | Se calcula dentro de `sync_service._process_message`, reutilizando la llamada de `classify()` (research.md §1-§2). |
| Sin reevaluación retroactiva | Columnas nuevas `NULL` por defecto en filas existentes; sin script de backfill (research.md §5). |

No quedan `NEEDS CLARIFICATION` pendientes en el Technical Context de plan.md.
