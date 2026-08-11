# Invoice Manager

Herramienta web para identificar, validar y archivar facturas de gasto recibidas por email, con
revisión humana obligatoria antes de cualquier escritura masiva. Ver
[.specify/memory/constitution.md](.specify/memory/constitution.md) para los principios del
proyecto y [specs/001-ingesta-facturas-email/](specs/001-ingesta-facturas-email/) para la
especificación, plan y tareas de la primera feature (ingesta y detección de facturas por email).

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

## Estructura

Ver `specs/001-ingesta-facturas-email/plan.md` § Project Structure para el detalle de `app/`.
