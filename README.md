# Invoice Manager

Herramienta web para identificar, validar y archivar facturas de gasto recibidas por email, con
revisión humana obligatoria antes de cualquier escritura masiva. Ver
[.specify/memory/constitution.md](.specify/memory/constitution.md) para los principios del
proyecto. Features implementadas hasta ahora:

- [specs/001-ingesta-facturas-email/](specs/001-ingesta-facturas-email/) — conectar una cuenta
  de correo, sincronizar y detectar documentos candidatos a factura de gasto.
- [specs/002-validacion-archivado-facturas/](specs/002-validacion-archivado-facturas/) —
  validar un documento candidato (proveedor activo, fecha, número, total) y confirmar su
  archivado a PROCESADA, gestionar el catálogo de proveedores, y reclasificar documentos mal
  clasificados automáticamente.
- [specs/003-sugerencia-datos-factura/](specs/003-sugerencia-datos-factura/) — precargar el
  formulario de validación con proveedor/fecha/número/total propuestos a partir del propio
  documento, siempre editables y sujetos a la misma confirmación humana explícita.
- [specs/004-conciliacion-bancaria/](specs/004-conciliacion-bancaria/) — conciliación bancaria:
  la persona autorizada aporta un extracto (CSV) para un periodo y el sistema compara cada
  factura PROCESADA de ese periodo con los movimientos, marcando coincidencias inequívocas como
  CONCILIADA, dejando en "NO ENCONTRADA EN EXTRACTO" las que no tienen coincidencia (nunca
  "impagada") y en PENDIENTE REVISIÓN CONCILIACIÓN las ambiguas, que la persona resuelve
  manualmente. También muestra los movimientos de gasto del extracto sin factura asociada.
- [specs/005-volumen-mensual-facturas/](specs/005-volumen-mensual-facturas/) — volumen mensual de
  facturas: en la pestaña Actividad, la persona autorizada consulta cuántas facturas PROCESADA se
  archivaron cada mes de un periodo (por fecha de emisión), y la media del periodo, distinguiendo
  la media de meses completos de la que incluye un mes parcial (el mes en curso, o el primer mes
  de la cuenta conectada si empezó a mitad de mes). Consulta de solo lectura.
- [specs/006-lotes-aprobacion-previa/](specs/006-lotes-aprobacion-previa/) — lotes con aprobación
  previa: sincronizar ya no clasifica ni guarda documentos candidato de inmediato — primero
  analiza el buzón y muestra un resumen (correos nuevos, correos con adjuntos candidatos); solo
  al aprobar explícitamente el lote se clasifica y se archiva. Si un correo falla al procesarse,
  el resto del lote sigue adelante y el fallido queda visible con su motivo, reintentable sin
  repetir los demás; si la ejecución se interrumpe, reanudarla continúa sin reprocesar lo ya
  guardado.

## Requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Puesta en marcha

```bash
uv sync
cp .env.example .env
# Rellena .env con tus credenciales (ver comentarios en .env.example)
uv run uvicorn app.main:app --reload
```

La app queda disponible en `http://localhost:8000`. Primero visita `/login` con una de las
identidades listadas en `AUTHORIZED_ACCOUNTS` y la contraseña de `APP_PASSWORD`.

## Variables de entorno

Todas las variables están documentadas en [.env.example](.env.example):

- `SESSION_SECRET`, `AUTHORIZED_ACCOUNTS`, `APP_PASSWORD` — sesión mínima de persona autorizada.
- `IMAP_*`, `GMAIL_*`, `GRAPH_*` — credenciales de conexión de buzón según proveedor.
- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ANTHROPIC_MONTHLY_BUDGET_USD` — clasificación acotada
  de candidatos (Principio VII de la constitution).
- `ATTACHMENT_STORE_DIR`, `SQLITE_DB_PATH` — almacenamiento local de adjuntos y base de datos.

## Tests

```bash
uv run pytest
uv run ruff check app
```

## Esquema de base de datos

El esquema vive en `app/db/migrations/*.sql`, aplicadas en orden por `init_db()` (ver
`specs/002-validacion-archivado-facturas/research.md` §1). Para añadir un cambio de esquema,
crea un nuevo archivo `NNNN_descripcion.sql` — nunca edites una migración ya aplicada.

## Estructura

Ver `specs/001-ingesta-facturas-email/plan.md` y `specs/002-validacion-archivado-facturas/plan.md`
§ Project Structure para el detalle de `app/`.
