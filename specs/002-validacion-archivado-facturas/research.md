# Research: Validación y Archivado con Revisión Humana

**Fase**: 0 — Outline & Research
**Fecha**: 2026-08-11
**Spec**: [spec.md](./spec.md)

Esta feature se construye directamente sobre la app ya implementada en `specs/001-ingesta-facturas-email/` (FastAPI + SQLite + Jinja2, ver su `plan.md`). No se introduce ningún cambio de stack; las decisiones aquí son de evolución del esquema y de reglas de negocio.

## 1. Evolución del esquema SQLite: de `schema.sql` único a migraciones versionadas

- **Decision**: Sustituir el `schema.sql` único de la feature 001 por una carpeta `app/db/migrations/` con archivos `NNNN_descripcion.sql` aplicados en orden y registrados en una tabla `schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT)`. El `schema.sql` actual pasa a ser `0001_initial.sql` sin cambios; esta feature añade `0002_validacion_archivado.sql`. `init_db()` aplica cualquier migración cuya versión no esté ya registrada, en una transacción por archivo.
- **Rationale**: Esta feature necesita (a) añadir `PROCESADA` a la lista de estados válidos de `candidate_documents.estado`, lo que en SQLite exige recrear la tabla porque no se puede alterar un `CHECK` existente con `ALTER TABLE` (research.md §2), y (b) añadir una tabla y varias columnas nuevas. El patrón `CREATE TABLE IF NOT EXISTS` de la feature 001 no soporta ninguna de las dos cosas sobre una base de datos que ya tiene la tabla creada. Dado que el proyecto seguirá añadiendo features que tocan el esquema (proveedores ya es la segunda), un mecanismo de migraciones versionado evita este problema de forma permanente, no solo para esta feature.
- **Alternatives considered**: Mantener `schema.sql` único y pedir borrar la base de datos local en cada cambio de esquema → descartado porque ya no es viable en cuanto exista un despliegue real con datos (aunque hoy el proyecto está en desarrollo, esta feature es el primer punto en el que un `DROP` destruiría trabajo de validación ya hecho).

## 2. Añadir `PROCESADA` al `CHECK` de `estado` en SQLite

- **Decision**: La migración `0002` recrea `candidate_documents` con el patrón estándar de SQLite para cambiar un `CHECK`/columna: crear `candidate_documents_new` con el `CHECK` ampliado (`... 'DUPLICADO IGNORADO', 'PROCESADA'`) y las columnas nuevas de validación (research.md §3), copiar los datos de la tabla vieja, `DROP TABLE candidate_documents`, `ALTER TABLE candidate_documents_new RENAME TO candidate_documents`, y recrear los índices.
- **Rationale**: Es el patrón documentado por SQLite para este caso (no soporta `ALTER TABLE ... ALTER COLUMN` ni modificar `CHECK` in place). Mantener el `CHECK` (en vez de quitarlo) sigue siendo importante: seguimos queriendo que la base de datos rechace por sí misma cualquier estado no reconocido.
- **Alternatives considered**: Quitar el `CHECK` de `estado` y validar solo en Python → descartado; el `CHECK` es una segunda barrera barata contra el Principio II (nunca `PROCESADA` sin pasar por la validación) que no queremos perder solo por comodidad de migración.

## 3. Campos de validación: ampliar `candidate_documents` en vez de tabla separada

- **Decision**: Añadir `proveedor_id`, `fecha_factura`, `numero_factura`, `total`, `es_nota_credito`, `validado_por`, `fecha_validacion` como columnas nullable directamente en `candidate_documents`, en vez de crear una tabla `document_validations` 1:1 aparte.
- **Rationale**: La relación es estrictamente 1:1 y siempre se necesitan juntos (detalle de un documento = sus datos de ingesta + su validación si la tiene); una tabla separada solo añadiría un `JOIN` a cada lectura sin aportar nada, ya que ninguna de las dos partes tiene un ciclo de vida independiente del otro.
- **Alternatives considered**: Tabla `document_validations` separada → descartada por la razón anterior; se reconsideraría solo si en el futuro un documento pudiera tener varias validaciones (no es el caso: FR-011 prohíbe cambiar el estado una vez resuelto).

## 4. Detección de "archivado duplicado" (FR-009) sin reorganizar archivos físicos

- **Decision**: En vez de generar una segunda copia del PDF con un nombre "legible" (fecha-proveedor-importe-número) y comprobar colisiones de nombre de archivo, la comprobación de FR-009 se hace a nivel de datos: un índice único parcial `(proveedor_id, fecha_factura, numero_factura) WHERE estado = 'PROCESADA'`. Si al confirmar el archivado ya existe otro documento `PROCESADA` con esa misma combinación, la operación se rechaza (409) y el documento se queda como está (no se archiva, no se sobrescribe nada) en vez de completarse.
- **Rationale**: El adjunto original ya vive de forma inmutable en `attachment_store` desde la feature 001 (Principio III/IV, un archivo por adjunto, sin reescritura). Añadir una segunda copia "legible" solo para darle un nombre bonito duplicaría almacenamiento y crearía un segundo lugar donde el Principio IV podría violarse, sin aportar ninguna capacidad nueva: el mismo efecto (nunca archivar dos veces la "misma" factura, nunca perder la anterior) se consigue con una restricción de unicidad sobre los datos ya validados. El nombre "legible" para descargas puede seguir generándose bajo demanda (`Content-Disposition`) a partir de esos mismos campos, sin persistirlo.
- **Alternatives considered**: Generar y comprobar un nombre de archivo físico real → descartado por lo anterior; añadiría complejidad y un segundo mecanismo de "no sobrescritura" redundante con el que ya existe.

## 5. Catálogo de proveedores: comparación exacta, sin fuzzy matching

- **Decision**: `proveedor_id` se resuelve por nombre exacto (normalizado a minúsculas/sin espacios extra) contra `providers.nombre`. Si no existe, la persona autorizada puede crearlo en el momento (User Story 2, FR-005) — no hay detección automática de "proveedores similares" ni fusión de duplicados.
- **Rationale**: spec.md deja explícitamente fuera de alcance la gestión avanzada de proveedores (fusión de duplicados, similaridad); un matching difuso además introduciría el riesgo de asociar una factura al proveedor equivocado sin evidencia clara, en tensión con el Principio I.
- **Alternatives considered**: Matching por similitud de texto (Levenshtein, etc.) → descartado, fuera de alcance de spec.md y añade riesgo de falsos positivos sin beneficio claro para el MVP.

## 6. Quién confirma: reutilizar la sesión de persona autorizada existente

- **Decision**: `validado_por` se rellena con la misma identidad de sesión ya usada en toda la feature 001 (`app/auth/session.py`, `get_current_user`), sin ninguna infraestructura nueva de usuarios/roles.
- **Rationale**: La constitution no pide gestión de roles múltiples todavía, y la feature 001 ya resolvió la autenticación mínima; reutilizarla evita duplicar trabajo.
- **Alternatives considered**: Ninguna — no hay una decisión real que tomar aquí, se documenta para dejar explícito que no hace falta tocar `app/auth/`.

## Resumen de resolución de Assumptions de spec.md

| Assumption en spec.md | Traducción técnica |
|---|---|
| Catálogo de proveedores mínimo | Tabla `providers` con nombre, identificador fiscal opcional, `activo` booleano — sin más campos ni funcionalidad de fusión/edición avanzada. |
| Activar proveedor sin salir de la validación | El endpoint de validación acepta crear el proveedor al vuelo si no existe (mismo request), en vez de exigir una llamada previa a `POST /api/providers`. |
| Estados finales no se reabren | No existe ningún endpoint de "des-procesar" ni "des-clasificar"; FR-011 se aplica devolviendo 409 si se intenta validar/reclasificar un documento que ya no está en REVISIÓN MANUAL. |
| Organización física del archivo | Diferida: no hay una segunda copia con nombre legible: el nombre se calcula al vuelo para descargas; la unicidad se garantiza a nivel de datos (research.md §4). |

No quedan `NEEDS CLARIFICATION` pendientes en el Technical Context de plan.md.
