# Feature Specification: Conciliación Bancaria

**Feature Branch**: `004-conciliacion-bancaria`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "Conciliación bancaria: la persona autorizada aporta un extracto bancario (por ejemplo, un CSV con fecha, importe y concepto de cada movimiento) para un periodo, y el sistema compara cada factura ya PROCESADA de ese periodo con los movimientos del extracto para encontrar una coincidencia razonable por importe, fecha y proveedor. Si encuentra una coincidencia inequívoca, la factura queda marcada como conciliada, enlazada a ese movimiento. Si no encuentra ninguna coincidencia, la factura se registra como \"no encontrada en el extracto\" — nunca como impagada, ya que la ausencia de coincidencia no es evidencia de impago. Si hay varias coincidencias posibles sin poder elegir una con seguridad, el caso queda pendiente de revisión manual para que la persona autorizada decida. La persona también puede ver, para el periodo conciliado, qué movimientos bancarios de gasto no tienen ninguna factura asociada (pendientes de justificar). Ninguna conciliación se realiza de forma automática recurrente: la persona autorizada inicia cada conciliación aportando el extracto correspondiente."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aportar un extracto y ver qué facturas tienen respaldo de pago (Priority: P1) 🎯 MVP

Como persona autorizada, quiero aportar un extracto bancario de un periodo y ver qué facturas ya
archivadas tienen un movimiento que las respalda y cuáles no, para saber cuáles necesitan
seguimiento sin tener que revisar el banco factura por factura.

**Why this priority**: Es el propósito central de la feature — sin esto no hay conciliación.

**Independent Test**: Puede probarse aportando un extracto con un movimiento que coincide
claramente con una factura PROCESADA y otro que no coincide con ninguna, y comprobando que la
primera queda conciliada y la segunda queda como "no encontrada en el extracto".

**Acceptance Scenarios**:

1. **Given** un extracto con un movimiento que coincide en importe, fecha próxima y proveedor con
   una factura PROCESADA del mismo periodo, **When** se ejecuta la conciliación, **Then** la
   factura queda conciliada, enlazada a ese movimiento.
2. **Given** una factura PROCESADA del periodo sin ningún movimiento que coincida en el extracto
   aportado, **When** se ejecuta la conciliación, **Then** la factura se marca como "no encontrada
   en el extracto" — nunca como impagada.
3. **Given** una factura PROCESADA fuera del periodo cubierto por el extracto, **When** se ejecuta
   la conciliación, **Then** esa factura no se evalúa ni cambia de estado.
4. **Given** un extracto ya aportado y procesado antes, **When** se vuelve a aportar el mismo
   extracto, **Then** no se duplican vínculos ya confirmados en la conciliación anterior.

---

### User Story 2 - Resolver manualmente una factura con varias coincidencias posibles (Priority: P2)

Como persona autorizada, quiero decidir yo misma cuál es el movimiento correcto cuando hay más de
uno igual de plausible para una factura, para no dejar que el sistema adivine.

**Why this priority**: Cubre el caso ambiguo que no se puede resolver con seguridad automática;
sin esta historia, esos casos se quedarían sin ninguna salida.

**Independent Test**: Puede probarse con una factura cuyo importe coincide con dos movimientos
distintos del extracto, comprobando que queda pendiente de revisión manual con ambos como
candidatos, y que al elegir uno la factura queda conciliada con ese movimiento.

**Acceptance Scenarios**:

1. **Given** una factura con dos o más movimientos igual de plausibles en el extracto, **When**
   se ejecuta la conciliación, **Then** la factura queda pendiente de revisión manual, con los
   movimientos candidatos visibles.
2. **Given** un caso pendiente de revisión manual, **When** la persona autorizada elige uno de
   los movimientos candidatos, **Then** la factura queda conciliada con ese movimiento y los
   demás candidatos dejan de proponerse para ella.
3. **Given** un caso pendiente de revisión manual, **When** la persona autorizada decide que
   ninguno de los candidatos corresponde a la factura, **Then** la factura pasa a "no encontrada
   en el extracto".

---

### User Story 3 - Ver los movimientos de gasto sin factura asociada (Priority: P2)

Como persona autorizada, quiero ver qué cargos del extracto no corresponden a ninguna factura
archivada, para saber qué gastos me faltan por documentar.

**Why this priority**: Da visibilidad sobre el sentido contrario de la conciliación (gasto sin
factura, no solo factura sin gasto); no es imprescindible para el valor mínimo de User Story 1.

**Independent Test**: Puede probarse con un extracto que incluya un cargo sin ninguna factura
correspondiente, comprobando que aparece en la lista de movimientos pendientes de justificar tras
procesar la conciliación.

**Acceptance Scenarios**:

1. **Given** un extracto con movimientos de cargo que no coinciden con ninguna factura, **When**
   la persona consulta el resultado de la conciliación, **Then** ve esos movimientos marcados
   como pendientes de justificar.
2. **Given** un movimiento de ingreso o un traspaso entre cuentas propias, **When** se procesa el
   extracto, **Then** no aparece en la lista de pendientes de justificar.

---

### Edge Cases

- ¿Qué ocurre si el extracto aportado tiene un formato no reconocible o le faltan datos
  esenciales (fecha o importe)? → Se rechaza la conciliación con un motivo claro, sin marcar
  ninguna factura.
- ¿Qué ocurre si el mismo movimiento podría corresponder a dos facturas distintas con igual
  importe? → Ninguna de las dos se concilia automáticamente con ese movimiento; ambas quedan
  pendientes de revisión manual en vez de asignar el movimiento a una al azar.
- ¿Qué ocurre si un extracto nuevo se solapa parcialmente con uno ya procesado? → Los movimientos
  ya vinculados en una conciliación anterior no se vuelven a proponer.
- ¿Qué ocurre con una factura que ya quedó conciliada o "no encontrada en el extracto"? → Es un
  estado estable: conciliaciones posteriores no la reevalúan automáticamente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir a la persona autorizada aportar un extracto bancario
  (fecha, importe y concepto de cada movimiento) para un periodo determinado.
- **FR-002**: El sistema DEBE comparar cada factura PROCESADA dentro del periodo del extracto
  contra los movimientos aportados, buscando coincidencia por importe, fecha próxima y proveedor.
- **FR-003**: El sistema DEBE marcar una factura como conciliada, enlazada a un movimiento
  concreto, únicamente cuando exista una coincidencia inequívoca.
- **FR-004**: El sistema NO DEBE marcar ninguna factura como impagada; la ausencia de coincidencia
  DEBE registrarse como "no encontrada en el extracto".
- **FR-005**: El sistema DEBE dejar pendiente de revisión manual cualquier factura con varias
  coincidencias posibles igual de plausibles, sin decidir automáticamente por ninguna.
- **FR-006**: El sistema DEBE permitir a la persona autorizada resolver un caso pendiente de
  revisión manual, eligiendo el movimiento correcto o descartando todos los candidatos.
- **FR-007**: El sistema DEBE permitir a la persona autorizada consultar, para un extracto
  procesado, los movimientos de cargo sin ninguna factura asociada.
- **FR-008**: El sistema NO DEBE incluir ingresos ni traspasos entre cuentas propias en la lista
  de movimientos pendientes de justificar.
- **FR-009**: El sistema NO DEBE volver a proponer ni duplicar una coincidencia sobre un
  movimiento ya vinculado en una conciliación anterior.
- **FR-010**: El sistema NO DEBE ejecutar ninguna conciliación de forma automática o recurrente;
  cada conciliación la inicia explícitamente la persona autorizada aportando el extracto.
- **FR-011**: El sistema DEBE rechazar un extracto con formato no reconocible o datos esenciales
  incompletos, sin marcar ninguna factura, indicando el motivo del rechazo.
- **FR-012**: El sistema NO DEBE evaluar facturas fuera del periodo cubierto por el extracto
  aportado.

### Key Entities

- **Extracto/Conciliación**: periodo cubierto, fecha en que se aportó, quién lo aportó, número de
  movimientos que contiene.
- **Movimiento Bancario**: fecha, importe, concepto, si es cargo o ingreso, y si ya está vinculado
  a una factura.
- **Vínculo de Conciliación**: relación entre una factura (documento PROCESADA) y un movimiento
  bancario, con su estado (conciliada, no encontrada en el extracto, pendiente de revisión
  manual).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Al aportar un extracto de hasta 200 movimientos, la persona ve el resultado completo
  de la conciliación en menos de 1 minuto.
- **SC-002**: El 100% de las facturas PROCESADA dentro del periodo del extracto terminan, tras la
  conciliación, en uno de tres estados: conciliada, no encontrada en el extracto, o pendiente de
  revisión manual — ninguna queda sin evaluar ni se marca como impagada.
- **SC-003**: El 0% de los movimientos ya vinculados en una conciliación anterior se vuelven a
  proponer o duplican un vínculo en conciliaciones posteriores.
- **SC-004**: Al menos el 90% de las coincidencias inequívocas (mismo importe, fecha próxima y
  proveedor identificable) se detectan sin intervención manual.

## Assumptions

- El extracto se aporta como archivo CSV con, como mínimo, fecha, importe y concepto por
  movimiento; otros formatos quedan fuera de alcance de esta primera versión.
- "Coincidencia inequívoca" se basa en importe exacto y una ventana de fechas razonable, junto con
  alguna señal de proveedor en el concepto; el criterio exacto se define en el plan técnico de
  esta feature.
- Una factura ya conciliada o marcada "no encontrada en el extracto" es un estado estable dentro
  de esta feature: no se reevalúa automáticamente en conciliaciones posteriores. Reabrir ese
  estado manualmente queda fuera de alcance de esta primera versión.
- Esta feature asume una sola cuenta bancaria y una sola divisa; múltiples cuentas o divisas
  distintas quedan fuera de alcance.
- No se contempla la descarga automática de extractos desde un banco (vía API bancaria); el
  extracto lo aporta manualmente la persona autorizada, coherente con el Principio V (control
  humano, sin tareas programadas).
