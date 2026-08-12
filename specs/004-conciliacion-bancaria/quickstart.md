# Quickstart: Conciliación Bancaria

**Spec**: [spec.md](./spec.md) · **Contratos**: [contracts/api.md](./contracts/api.md) ·
**Modelo de datos**: [data-model.md](./data-model.md)

Requiere al menos una factura en estado `PROCESADA` (feature 002) con `fecha_factura` y `total`
conocidos.

## Preparar un CSV de prueba

```csv
fecha,importe,concepto
2026-07-05,-120.00,PAGO PROVEEDOR TEST SL
2026-07-12,-45.00,SUMINISTRO ELECTRICO
2026-08-01,1500.00,NOMINA
```

## Escenario 1 — Conciliación automática inequívoca (User Story 1)

1. Archivar una factura (feature 002) con `total: 120.00` y `fecha_factura` cercana a
   `2026-07-05`.
2. `POST /api/reconciliations` con el CSV de arriba.
3. **Resultado esperado**: `201 Created`, `conciliadas: 1`. `GET
   /api/candidate-documents/{id}` de esa factura muestra `estado_conciliacion: "CONCILIADA"` y
   `movimiento_conciliado` con importe `-120.0`.

## Escenario 2 — Sin coincidencia → "no encontrada", nunca "impagada" (FR-004)

1. Archivar otra factura con `total: 999.00` (sin ningún movimiento parecido en el CSV).
2. Repetir el `POST /api/reconciliations` (o incluir esta factura en el mismo periodo).
3. **Resultado esperado**: `estado_conciliacion: "NO ENCONTRADA EN EXTRACTO"` — nunca
   "impagada", ni ningún otro estado que implique impago.

## Escenario 3 — Ambigüedad → revisión manual (User Story 2)

1. Archivar dos facturas distintas con exactamente `total: 45.00` y fechas dentro de la misma
   ventana de ±10 días respecto a `2026-07-12`.
2. Añadir al CSV un segundo movimiento de `-45.00` en una fecha cercana.
3. `POST /api/reconciliations`.
4. **Resultado esperado**: ambas facturas quedan `PENDIENTE REVISIÓN CONCILIACIÓN` (ningún
   movimiento se asigna al azar).
5. `POST /api/candidate-documents/{id}/reconcile` con `{"movimiento_id": <uno de los dos>}` sobre
   una de ellas.
6. **Resultado esperado**: esa factura pasa a `CONCILIADA` y sus propios candidatos se limpian;
   la otra sigue `PENDIENTE REVISIÓN CONCILIACIÓN` con su lista de candidatos intacta. Si sobre
   esa otra se intenta `POST .../reconcile` eligiendo el mismo movimiento ya vinculado, la
   respuesta es `409 Conflict` (índice único — el movimiento no puede pertenecer a dos facturas).

## Escenario 4 — Movimientos pendientes de justificar (User Story 3)

1. Sobre el CSV del Escenario 1 (que incluye la fila de "SUMINISTRO ELECTRICO", `-45.00`, sin
   ninguna factura archivada que coincida).
2. `GET /api/reconciliations/{id}`.
3. **Resultado esperado**: ese movimiento aparece en `movimientos_pendientes_de_justificar`; la
   fila de `1500.00` (ingreso, "NOMINA") **no** aparece ahí (FR-008).

## Escenario 5 — Extracto inválido (FR-011)

1. `POST /api/reconciliations` con un CSV al que le falta la columna `importe`.
2. **Resultado esperado**: `422 Unprocessable Entity`; `GET /api/reconciliations` (o comprobar
   directamente) confirma que no se creó ningún `BankStatement` ni se tocó ninguna factura.

## Validación de principios no negociables

- **Principio I**: ninguna coincidencia ambigua se resuelve por adivinanza — Escenario 3 queda
  pendiente en vez de elegir un movimiento al azar.
- **Principio V**: la conciliación solo ocurre al llamar explícitamente a
  `POST /api/reconciliations`; no hay ningún proceso en segundo plano que la dispare.
- **Principio VI**: el Escenario 2 demuestra literalmente la regla del principio — "no encontrada
  en el extracto", nunca "impagada".
