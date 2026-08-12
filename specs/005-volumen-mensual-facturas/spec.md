# Feature Specification: Volumen Mensual de Facturas

**Feature Branch**: `005-volumen-mensual-facturas`

**Created**: 2026-08-12

**Status**: Draft

**Input**: User description: "Volumen mensual de facturas: la persona autorizada quiere consultar cuántas facturas de gasto en estado PROCESADA se han archivado por mes, y su media, para estimar la carga administrativa y detectar variaciones en el tiempo. El recuento de cada mes se basa en la fecha de emisión de la factura (no en la fecha del correo ni en la fecha de validación), y solo cuenta facturas en estado PROCESADA. Cuando el periodo consultado incluye el mes en curso (todavía no terminado), la media debe calcularse dos veces: una solo con meses completos y otra que incluye el mes parcial, dejando claro cuál es cuál. Esta consulta es de solo lectura: no crea, modifica ni archiva ninguna factura; se apoya únicamente en los datos ya validados y archivados por las features anteriores."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver el recuento mensual de facturas procesadas (Priority: P1) 🎯 MVP

Como persona autorizada, quiero ver cuántas facturas de gasto quedaron archivadas (PROCESADA) en
cada mes de un periodo, para estimar la carga administrativa y detectar variaciones sin contar
manualmente.

**Why this priority**: Es el propósito central de la feature — sin el recuento por mes no hay
métrica que consultar.

**Independent Test**: Puede probarse archivando facturas PROCESADA con distintas fechas de
emisión repartidas en varios meses, y comprobando que el recuento de cada mes coincide
exactamente con las facturas cuya fecha de emisión cae en ese mes.

**Acceptance Scenarios**:

1. **Given** varias facturas PROCESADA con fechas de emisión en distintos meses de un periodo,
   **When** se consulta el volumen mensual de ese periodo, **Then** se muestra el número de
   facturas de cada mes, contado por fecha de emisión.
2. **Given** documentos en estados distintos de PROCESADA (REVISIÓN MANUAL, NO ES FACTURA,
   FACTURA DE VENTA, DUPLICADO IGNORADO), **When** se calcula el recuento mensual, **Then** esos
   documentos no incrementan ningún mes.
3. **Given** una factura PROCESADA cuya fecha de emisión queda fuera del periodo consultado,
   **When** se calcula el recuento, **Then** esa factura no se cuenta en el periodo mostrado.
4. **Given** un mes del periodo sin ninguna factura PROCESADA, **When** se consulta el volumen
   mensual, **Then** ese mes aparece con recuento 0 en vez de omitirse silenciosamente.

---

### User Story 2 - Ver la media mensual, distinguiendo meses completos de meses parciales (Priority: P2)

Como persona autorizada, quiero ver la media de facturas por mes de un periodo, sabiendo si
incluye o no meses que todavía no han terminado de contarse, para no sacar conclusiones
equivocadas sobre la carga administrativa real.

**Why this priority**: La media sin este matiz puede engañar (un mes en curso con pocos días
transcurridos parece "bajo" y distorsiona la media); depende de que exista ya el recuento mensual
de la Historia de Usuario 1.

**Independent Test**: Puede probarse consultando un periodo que incluya el mes en curso y
comprobando que se muestran dos medias claramente diferenciadas: una solo con meses completos y
otra que incluye el mes parcial.

**Acceptance Scenarios**:

1. **Given** un periodo formado íntegramente por meses ya terminados, **When** se consulta la
   media mensual, **Then** se muestra una única media, calculada sobre esos meses completos.
2. **Given** un periodo que incluye el mes en curso (todavía no terminado), **When** se consulta
   la media mensual, **Then** se muestran dos medias etiquetadas de forma distinguible: la de
   meses completos y la que incluye el mes en curso.
3. **Given** un periodo que incluye el primer mes de actividad de la cuenta conectada (mes en el
   que se conectó a mitad de mes), **When** se consulta la media mensual, **Then** ese primer mes
   se trata como parcial igual que el mes en curso, y no se cuenta como mes completo.

---

### Edge Cases

- ¿Qué ocurre si todavía no se ha archivado ninguna factura PROCESADA en todo el periodo
  consultado? → Se muestran los meses del periodo con recuento 0 y ninguna media (0 meses
  completos con datos), sin error.
- ¿Qué ocurre si el periodo consultado es anterior a que existiera cualquier cuenta de correo
  conectada? → Esos meses se muestran con recuento 0, ya que no hay ninguna factura PROCESADA que
  pueda pertenecer a ellos; no se presentan como "sin datos" distinto de "cero facturas", porque
  el sistema no reconstruye actividad previa a su propio histórico (ver Assumptions).
- ¿Qué ocurre si una factura PROCESADA se reclasifica o su fecha de emisión se corrige después de
  archivada? → El recuento mensual refleja siempre el estado y la fecha de emisión actuales en el
  momento de la consulta; no se guarda una foto fija del mes en que se archivó originalmente.
- ¿Qué ocurre si el periodo consultado abarca más de un año? → El recuento y la media se agrupan
  por año y mes (p. ej. "2026-01"), nunca solo por número de mes, para no mezclar enero de un año
  con enero de otro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE mostrar, para un periodo solicitado por la persona autorizada, el
  número de facturas en estado PROCESADA cuya fecha de emisión cae en cada mes de ese periodo.
- **FR-002**: El sistema NO DEBE contar en el volumen mensual ningún documento cuyo estado sea
  distinto de PROCESADA.
- **FR-003**: El sistema DEBE basar el recuento mensual exclusivamente en la fecha de emisión de
  la factura, nunca en la fecha del correo de origen ni en la fecha de su validación.
- **FR-004**: El sistema NO DEBE contar en el periodo consultado ninguna factura PROCESADA cuya
  fecha de emisión quede fuera de ese periodo.
- **FR-005**: El sistema DEBE mostrar con recuento 0, no omitir, cualquier mes del periodo
  consultado que no tenga ninguna factura PROCESADA.
- **FR-006**: El sistema DEBE calcular la media mensual de facturas del periodo consultado.
- **FR-007**: El sistema DEBE distinguir, cuando el periodo consultado incluya un mes parcial
  (el mes en curso, o el primer mes de actividad de la cuenta conectada si esta se conectó a
  mitad de mes), la media calculada solo con meses completos de la media que incluye el mes
  parcial, de forma que la persona autorizada pueda identificar cuál es cuál sin ambigüedad.
- **FR-008**: El sistema NO DEBE mezclar silenciosamente un mes parcial dentro del cálculo de
  "meses completos"; un mes parcial solo puede aparecer en la media que lo declara explícitamente
  incluido.
- **FR-009**: La consulta del volumen mensual DEBE ser de solo lectura: no debe crear, modificar,
  archivar ni cambiar el estado de ninguna factura.

### Key Entities

- **Factura de gasto (existente)**: se reutiliza el documento PROCESADA ya definido en
  specs/002-validacion-archivado-facturas/ — esta feature solo lee su `fecha_factura` y `estado`,
  no añade campos nuevos.
- **Recuento Mensual**: agregación de solo lectura por año-mes; número de facturas PROCESADA cuya
  fecha de emisión cae en ese mes. No se persiste — se calcula en el momento de la consulta.
- **Media del Periodo**: par de valores calculados sobre los Recuentos Mensuales de un periodo
  consultado — media de meses completos, y media que incluye el mes parcial (cuando el periodo
  contiene alguno).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El recuento de cada mes mostrado cuadra exactamente con el número de facturas
  PROCESADA cuya fecha de emisión pertenece a ese mes, verificable por conteo manual sobre un
  conjunto de prueba.
- **SC-002**: El 100% de los meses del periodo consultado aparece en el resultado, incluidos los
  que tienen recuento 0.
- **SC-003**: Cuando el periodo consultado incluye un mes parcial, la persona autorizada puede
  identificar, sin ambigüedad y sin consultar ninguna otra pantalla, cuál media incluye ese mes y
  cuál no.
- **SC-004**: La persona autorizada obtiene el volumen mensual de un periodo típico (12 meses) en
  menos de 5 segundos desde que lo solicita.

## Assumptions

- El periodo por defecto al abrir la consulta es "los últimos 12 meses completos más el mes en
  curso"; la persona autorizada puede ajustar el periodo a otro rango de meses.
- La "línea base histórica" mencionada en spec.md (raíz) — el histórico capturado durante la
  migración inicial, comparado fuera del repositorio — es un proceso externo y puntual, ajeno a
  esta feature: esta consulta solo agrega datos que ya existen como facturas PROCESADA dentro del
  sistema, sin reconstruir ni estimar actividad anterior a la primera sincronización de la cuenta
  conectada.
- Solo existe una cuenta de correo conectada por persona autorizada (según
  specs/001-ingesta-facturas-email/), por lo que el único mes potencialmente parcial por inicio de
  actividad es el mes de conexión de esa cuenta; no se contempla combinar históricos de varias
  cuentas con fechas de conexión distintas en esta primera versión.
- Esta consulta no incluye desglose por proveedor ni por otros campos — solo el recuento por mes y
  la media del periodo, coherente con la Historia de Usuario 8 de spec.md (raíz).
