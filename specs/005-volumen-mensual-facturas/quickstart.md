# Quickstart: Volumen Mensual de Facturas

**Spec**: [spec.md](./spec.md) · **Contratos**: [contracts/api.md](./contracts/api.md) ·
**Modelo de datos**: [data-model.md](./data-model.md)

Requiere una cuenta de correo conectada (feature 001) y al menos una factura en estado
`PROCESADA` (feature 002) con `fecha_factura` conocida.

## Escenario 1 — Recuento por mes, contando solo PROCESADA (User Story 1)

1. Archivar tres facturas `PROCESADA` con `fecha_factura` en el mismo mes, y una cuarta en
   `REVISIÓN MANUAL` con fecha en ese mismo mes.
2. `GET /api/metrics/volumen-mensual?desde=<ese mes>&hasta=<ese mes>`.
3. **Resultado esperado**: el mes aparece con `total: 3` (la que está en `REVISIÓN MANUAL` no
   cuenta).

## Escenario 2 — Meses sin facturas no se omiten (FR-005)

1. Archivar una factura `PROCESADA` en un mes concreto, sin ninguna otra factura en los dos meses
   siguientes.
2. `GET /api/metrics/volumen-mensual?desde=<mes de la factura>&hasta=<dos meses después>`.
3. **Resultado esperado**: `meses` contiene 3 entradas (los tres meses del rango), las dos sin
   factura con `total: 0`.

## Escenario 3 — Media distingue meses completos del mes en curso (User Story 2)

1. Archivar facturas `PROCESADA` en varios meses ya terminados, y una factura más con
   `fecha_factura` en el mes en curso.
2. `GET /api/metrics/volumen-mensual` con `hasta` incluyendo el mes en curso.
3. **Resultado esperado**: el mes en curso aparece con `completo: false`;
   `media_meses_completos` se calcula solo con los meses terminados;
   `media_con_mes_parcial` incluye también el mes en curso; ambos valores son distintos entre sí
   (salvo coincidencia numérica).

## Escenario 4 — Primer mes de conexión de la cuenta también es parcial

1. Simular una cuenta cuya `fecha_conexion` cae a mitad de un mes ya terminado.
2. `GET /api/metrics/volumen-mensual` con `desde` igual a ese mes.
3. **Resultado esperado**: ese mes aparece con `completo: false` aunque ya haya terminado, y no
   se cuenta dentro de `media_meses_completos`.

## Escenario 5 — Periodo inválido (contracts/api.md)

1. `GET /api/metrics/volumen-mensual?desde=2026-13&hasta=2026-01` (mes inválido y rango invertido).
2. **Resultado esperado**: `422 Unprocessable Entity`.

## Validación de principios no negociables

- **Principio I**: ningún mes muestra un número inventado — Escenario 2 demuestra que un mes sin
  facturas se informa como `0`, nunca se estima ni se omite.
- **Principio V**: la consulta solo ocurre al llamar explícitamente a
  `GET /api/metrics/volumen-mensual` (al abrir la pestaña Actividad o cambiar el periodo); no hay
  ningún cálculo programado en segundo plano.
