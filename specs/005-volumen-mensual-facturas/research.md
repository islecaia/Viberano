# Research: Volumen Mensual de Facturas

**Fase**: 0 — Outline & Research
**Fecha**: 2026-08-12
**Spec**: [spec.md](./spec.md)

Esta feature extiende la app ya construida en `specs/001-.../002-.../003-.../004-.../`. No se
introduce ningún stack nuevo.

## 1. Agrupación por mes: cálculo en la consulta, sin persistir nada nuevo

- **Decision**: El recuento mensual se calcula con una consulta SQL agrupando
  `candidate_documents.fecha_factura` por año-mes (`strftime('%Y-%m', fecha_factura)`), filtrando
  `estado = 'PROCESADA'` y el rango de fechas del periodo pedido. No se crea ninguna tabla ni
  columna nueva — es una lectura agregada sobre datos ya existentes desde la feature 001/002.
- **Rationale**: `fecha_factura` ya se almacena como texto ISO (`YYYY-MM-DD`), así que
  `strftime('%Y-%m', ...)` agrupa correctamente por año-mes sin ambigüedad entre años (spec.md,
  Edge Cases). Cumple FR-009 (solo lectura) de forma trivial: no hay ninguna escritura implicada.
- **Alternatives considered**: Mantener una tabla de agregados (`monthly_metrics`) actualizada al
  archivar cada factura → descartado; añadiría complejidad de sincronización (mantenerla al día
  ante reclasificaciones o correcciones de `fecha_factura`) sin necesidad, dado que el volumen de
  datos de esta app (facturas de una microempresa) hace trivial calcularlo al vuelo (SC-004: <5s
  para un periodo de 12 meses).

## 2. Qué mes se considera "parcial" (FR-007, FR-008)

- **Decision**: Un mes se considera parcial si es (a) el mes en curso (todavía no ha terminado
  el día de la consulta), o (b) el mes en que se conectó la cuenta de correo
  (`mailbox_accounts.fecha_conexion`), si esa conexión ocurrió después del día 1 de ese mes. Todos
  los demás meses del periodo cuentan como "completos" para la media. Si el periodo no incluye
  ningún mes parcial, se muestra una única media (Acceptance Scenario 1 de User Story 2).
- **Rationale**: Es la lectura más directa de spec.md, User Story 2, Acceptance Scenario 3 y de la
  Assumption sobre la "línea base histórica": esta app solo puede contar facturas que existen en
  su propia base de datos, y esa base empieza a llenarse desde que se conecta la cuenta. Un mes
  anterior o parcialmente cubierto por esa conexión no tiene el mismo significado que un mes
  íntegramente cubierto.
- **Alternatives considered**: Considerar parcial solo el mes en curso, ignorando el mes de
  conexión → descartado porque produciría el mismo sesgo que motiva FR-007 (un mes con pocos días
  de datos reales parece "bajo" y distorsiona la media) pero al principio del histórico en vez de
  al final; spec.md, User Story 2, Acceptance Scenario 3 pide explícitamente tratarlo igual que el
  mes en curso.

## 3. Periodo por defecto y formato de los parámetros de consulta

- **Decision**: Si la persona no especifica un periodo, se usa "los últimos 12 meses completos
  más el mes en curso" (spec.md, Assumptions), calculado desde la fecha de hoy. El endpoint acepta
  `desde`/`hasta` en formato `YYYY-MM` (granularidad de mes, coherente con que esta feature nunca
  necesita precisión de día).
- **Rationale**: Es un periodo estándar y predecible para una métrica operativa mensual; permite
  a la persona autorizada ajustar el rango sin imponerle un selector de fechas exactas que esta
  feature no necesita (la granularidad real es el mes, no el día).
- **Alternatives considered**: Periodo por defecto = año en curso completo → descartado porque en
  enero mostraría un único mes, poco útil para "detectar variaciones" (spec.md, motivación de
  User Story 1); 12 meses rodantes da siempre una serie con contexto suficiente.

## 4. Dónde vive esta consulta en la navegación

- **Decision**: Se aloja en la pestaña **Actividad** de la barra inferior (`app/templates/base.html`),
  que hasta ahora era un placeholder ("Próximamente") sin propósito asignado. Sustituye el texto
  genérico anterior ("Historial de sincronizaciones y acciones sobre tus facturas") por esta
  consulta de volumen mensual.
- **Rationale**: DESIGN.md fija explícitamente "cuatro destinos estables" en la barra inferior
  (Facturas, Proveedores, Conciliación, Actividad); añadir una quinta pestaña entraría en
  conflicto directo con ese documento. De las cuatro, Actividad es la única sin una feature que la
  reclame todavía. Decisión confirmada explícitamente por el usuario durante la planificación
  (no inferida) al presentarse el conflicto con DESIGN.md.
- **Alternatives considered**: Tarjeta resumen dentro de la pantalla de Facturas → descartada por
  decisión del usuario; Nueva quinta pestaña con enmienda a DESIGN.md → descartada por decisión
  del usuario (habría requerido modificar DESIGN.md).

## Resumen de resolución de Assumptions de spec.md

| Assumption en spec.md | Traducción técnica |
|---|---|
| Periodo por defecto = últimos 12 meses completos + mes en curso | research.md §3 |
| La línea base histórica es un proceso externo, fuera de esta feature | research.md §1: solo se agrega lo que ya existe en `candidate_documents` |
| Una sola cuenta conectada por persona | research.md §2: un único `fecha_conexion` relevante para el mes parcial inicial |
| Sin desglose por proveedor | No se añade ningún `GROUP BY` adicional a la consulta |

No quedan `NEEDS CLARIFICATION` pendientes en el Technical Context de plan.md.
