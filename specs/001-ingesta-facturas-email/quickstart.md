# Quickstart: Ingesta y Detección de Facturas por Email

**Spec**: [spec.md](./spec.md) · **Contratos**: [contracts/api.md](./contracts/api.md) ·
**Modelo de datos**: [data-model.md](./data-model.md)

Esta guía valida de extremo a extremo las tres historias de usuario de la spec usando una cuenta
IMAP de prueba (evita depender de credenciales reales de Gmail/Graph para validar localmente).

## Prerrequisitos

- Python 3.11+ y `uv` instalados.
- Variables de entorno de desarrollo configuradas (`.env.local`): credenciales de una cuenta IMAP
  de pruebas con al menos 3 correos de prueba (uno con adjunto PDF de factura, uno sin adjuntos,
  uno con una factura de venta emitida por el propio usuario) y una clave de Anthropic API con
  límite de gasto bajo (research.md §4).
- Sesión de persona autorizada válida (`isleca@protonmail.com` en el entorno de desarrollo).

## Puesta en marcha

```bash
uv sync
uv run uvicorn app.main:app --reload
```

## Escenario 1 — Conectar una cuenta de correo (User Story 1)

1. `POST /api/mailbox-accounts` con `proveedor: "imap"` y las credenciales de prueba.
2. **Resultado esperado**: `201 Created`, `estado: "conectada"`.
3. `GET /api/mailbox-accounts/current` → confirma `estado: "conectada"`.

## Escenario 2 — Sincronizar y detectar candidatos (User Story 2)

1. `POST /api/mailbox-accounts/{id}/sync` → `202 Accepted` con `sync_run_id`.
2. Sondear `GET /api/sync-runs/{sync_run_id}` hasta `estado: "completada"`.
3. **Resultado esperado**:
   - El correo con adjunto PDF de factura genera un `DocumentoCandidato` en `REVISIÓN MANUAL` (o
     el estado que determine la clasificación, nunca `PROCESADA`).
   - El correo sin adjuntos no genera ningún candidato.
   - El correo de factura de venta genera un candidato en estado `FACTURA DE VENTA`.
4. Repetir el paso 1 sin nuevos correos en el buzón.
   **Resultado esperado**: `candidatos_generados: 0` en la segunda sincronización y ningún
   `DocumentoCandidato` duplicado (valida SC-005 y FR-009).

## Escenario 3 — Revisar los candidatos detectados (User Story 3)

1. `GET /api/candidate-documents?estado=REVISIÓN MANUAL` → lista el candidato del escenario 2.
2. `GET /api/candidate-documents/{id}` → confirma remitente, asunto, fecha y `motivo_clasificacion`.
3. `GET /api/candidate-documents/{id}/attachment` → descarga el PDF; comparar su contenido byte a
   byte con el adjunto original en el buzón de pruebas para validar SC-003 (no se modifica el
   original).

## Validación de principios no negociables

- **Principio III / SC-003**: tras los 3 escenarios, el correo y el adjunto originales en el
  buzón IMAP de pruebas deben seguir existiendo, sin mover ni marcar como leídos de forma distinta
  a como lo haría un cliente de correo normal de solo lectura.
- **Principio V**: no debe haber ningún proceso en segundo plano ejecutando sincronizaciones sin
  que el paso 1 del Escenario 2 se haya invocado explícitamente.
- **Principio I / FR-008**: si se apaga temporalmente el acceso a la Anthropic API antes del
  Escenario 2, el correo con factura debe seguir generando un candidato en `REVISIÓN MANUAL` (no
  desaparecer ni clasificarse falsamente como `NO ES FACTURA`).
