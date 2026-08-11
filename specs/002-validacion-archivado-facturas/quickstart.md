# Quickstart: Validación y Archivado con Revisión Humana

**Spec**: [spec.md](./spec.md) · **Contratos**: [contracts/api.md](./contracts/api.md) ·
**Modelo de datos**: [data-model.md](./data-model.md)

Requiere que ya exista al menos un documento candidato en `REVISIÓN MANUAL` (producido por
`specs/001-ingesta-facturas-email/`, por ejemplo vía `scripts/send_test_email.py`).

## Prerrequisitos

- App de la feature 001 funcionando (`uv run uvicorn app.main:app --reload`) con sesión de
  persona autorizada iniciada.
- Al menos un documento candidato en estado `REVISIÓN MANUAL` (`GET /api/candidate-documents?estado=REVISIÓN MANUAL`).

## Escenario 1 — Crear un proveedor y validar un documento (User Story 1 y 2)

1. `POST /api/candidate-documents/{id}/validate` con `proveedor_nombre_nuevo: "Proveedor de Prueba SL"`,
   `fecha_factura`, `numero_factura` y `total` de un documento en `REVISIÓN MANUAL`.
2. **Resultado esperado**: `200 OK`, el proveedor se crea activo, y el documento pasa a
   `estado: "PROCESADA"` con `validado_por` y `fecha_validacion` rellenos.
3. `GET /api/candidate-documents/{id}` → confirma que sigue devolviendo los cuatro campos y que
   el adjunto original (`GET /api/candidate-documents/{id}/attachment`, de la feature 001) sigue
   siendo accesible sin cambios (Principio III).

## Escenario 2 — Bloquear el archivado con proveedor inactivo (User Story 1 escenario 3)

1. `PATCH /api/providers/{id}` con `{ "activo": false }` sobre el proveedor creado en el
   Escenario 1.
2. Intentar validar otro documento en `REVISIÓN MANUAL` con ese mismo `proveedor_id`.
3. **Resultado esperado**: `409 Conflict`; el documento sigue en `REVISIÓN MANUAL`.
4. `PATCH /api/providers/{id}` con `{ "activo": true }` y repetir el paso 2.
5. **Resultado esperado**: ahora `200 OK` y el documento pasa a `PROCESADA`.

## Escenario 3 — Reclasificar sin validar (User Story 3)

1. `POST /api/candidate-documents/{id}/reclassify` con `{ "estado": "NO ES FACTURA" }` sobre un
   documento en `REVISIÓN MANUAL` distinto de los anteriores.
2. **Resultado esperado**: `200 OK`, `estado: "NO ES FACTURA"`, sin que se haya pedido
   proveedor/fecha/número/total.
3. Repetir la llamada del paso 1 sobre el mismo documento.
4. **Resultado esperado**: `409 Conflict` — ya no está en `REVISIÓN MANUAL` (FR-011).

## Escenario 4 — Colisión de archivado (FR-009)

1. Validar y archivar un documento con `proveedor_id`, `fecha_factura` y `numero_factura` X.
2. Intentar validar y archivar un segundo documento distinto con exactamente el mismo
   `proveedor_id` + `fecha_factura` + `numero_factura`.
3. **Resultado esperado**: `409 Conflict` en el segundo intento; el primer documento sigue
   `PROCESADA` sin alteraciones (no se sobrescribe nada).

## Validación de principios no negociables

- **Principio I**: en ningún escenario el sistema completa un campo de validación por su cuenta;
  siempre lo introduce la persona autorizada.
- **Principio II**: ningún documento llega a `PROCESADA` sin los cuatro campos y un proveedor
  activo (Escenarios 1 y 2).
- **Principio III/IV**: el adjunto original nunca cambia, y el Escenario 4 demuestra que un
  archivado duplicado se rechaza en vez de sobrescribir.
