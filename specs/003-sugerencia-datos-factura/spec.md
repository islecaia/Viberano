# Feature Specification: Sugerencia Automática de Datos de Factura

**Feature Branch**: `003-sugerencia-datos-factura`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "Sugerencia automática de datos de factura: al mostrar un documento candidato en REVISIÓN MANUAL, el sistema propone valores de proveedor, fecha, número de factura y total leídos del propio documento (adjunto), precargando el formulario de validación con esas sugerencias en lugar de dejarlo en blanco. La persona autorizada ve claramente que son sugerencias, no hechos confirmados, y debe revisarlas, corregirlas si hace falta y confirmarlas explícitamente antes de archivar — el sistema nunca archiva con un valor sugerido sin que la persona lo haya validado. Si el sistema no tiene confianza suficiente en un campo, lo deja vacío en vez de rellenarlo con una suposición."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver sugerencias precargadas al revisar un documento (Priority: P1) 🎯 MVP

Como persona autorizada, quiero que el formulario de validación de un documento en REVISIÓN
MANUAL ya venga con proveedor, fecha, número y total propuestos a partir del propio documento,
para no tener que teclearlos todos desde cero mirando el PDF.

**Why this priority**: Es el valor central de la feature — reduce el trabajo manual de la
validación sin cambiar ninguna de sus garantías.

**Independent Test**: Puede probarse abriendo un documento en REVISIÓN MANUAL cuyo adjunto
contenga datos identificables, y comprobando que el formulario de validación aparece precargado
con esos cuatro campos, marcados visualmente como sugerencia y no como dato confirmado.

**Acceptance Scenarios**:

1. **Given** un documento en REVISIÓN MANUAL cuyo adjunto contiene datos identificables, **When**
   la persona autorizada abre su detalle, **Then** el formulario de validación aparece precargado
   con proveedor, fecha, número y total sugeridos, distinguibles visualmente de un dato ya
   confirmado.
2. **Given** un campo que el sistema no pudo identificar con confianza suficiente, **When** se
   muestra el formulario, **Then** ese campo aparece vacío en lugar de con un valor supuesto.
3. **Given** un documento cuyo adjunto no contiene ningún dato identificable (o no se pudo
   analizar), **When** la persona abre su detalle, **Then** el formulario aparece vacío, igual
   que hoy, sin bloquear ni entorpecer la revisión manual.
4. **Given** un formulario con campos precargados, **When** la persona los modifica y confirma el
   archivado, **Then** se archivan los valores finales que ella confirmó, editados o no, exactamente
   con las mismas comprobaciones ya exigidas (proveedor activo, campos completos, sin colisión).

---

### User Story 2 - Sugerir un proveedor nuevo cuando no existe en el catálogo (Priority: P2)

Como persona autorizada, quiero que si el proveedor identificado en el documento no está en el
catálogo, el sistema me lo proponga como proveedor nuevo en vez de dejar el campo vacío, para
poder confirmarlo o corregirlo en el mismo paso.

**Why this priority**: Completa el valor de User Story 1 en el caso, muy habitual, de una primera
factura de un proveedor todavía no registrado; no es imprescindible para el MVP porque el
formulario ya permite añadir un proveedor nuevo manualmente.

**Independent Test**: Puede probarse con un documento cuyo remitente/contenido no coincide con
ningún proveedor activo existente, comprobando que el formulario propone su nombre como
"proveedor nuevo" en vez de dejarlo sin sugerencia.

**Acceptance Scenarios**:

1. **Given** un nombre de proveedor identificado en el documento que no coincide con ninguno del
   catálogo, **When** se muestra el formulario, **Then** aparece precargado como propuesta de
   proveedor nuevo, editable antes de confirmar.
2. **Given** un nombre de proveedor identificado que sí coincide con uno ya activo en el
   catálogo, **When** se muestra el formulario, **Then** aparece seleccionado ese proveedor
   existente en vez de proponerlo como nuevo.

---

### Edge Cases

- ¿Qué ocurre si el adjunto no tiene texto extraíble (p. ej. una imagen sin contenido
  reconocible)? → No se sugiere ningún campo; el formulario queda vacío, como sucede hoy.
- ¿Qué ocurre si el servicio que genera las sugerencias falla o no responde? → El documento se
  sigue pudiendo abrir y validar con el formulario vacío; el fallo de la sugerencia nunca bloquea
  la revisión manual.
- ¿Qué ocurre si dos interpretaciones de un campo son igual de plausibles (p. ej. una fecha en
  formato ambiguo)? → Ante esa ambigüedad, el campo se deja vacío en lugar de arriesgar un valor
  incorrecto.
- ¿Qué ocurre con un documento que ya no está en REVISIÓN MANUAL (por ejemplo, ya PROCESADA)? →
  No se generan ni se muestran sugerencias; esta feature solo aplica mientras el documento sigue
  pendiente de revisión.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE proponer valores de proveedor, fecha de factura, número de factura
  y total a partir del contenido del propio documento candidato, para documentos en REVISIÓN
  MANUAL.
- **FR-002**: El sistema DEBE mostrar estas sugerencias precargadas en el formulario de
  validación, distinguibles visualmente de un dato ya confirmado por una persona.
- **FR-003**: El sistema NO DEBE completar un campo con una sugerencia si su confianza es
  insuficiente; en ese caso el campo DEBE quedar vacío.
- **FR-004**: El sistema DEBE permitir a la persona autorizada modificar cualquier valor sugerido
  antes de confirmar el archivado.
- **FR-005**: El sistema NO DEBE archivar ningún documento usando un valor sugerido sin que la
  persona autorizada haya confirmado explícitamente el archivado (misma confirmación ya exigida
  por la validación y archivado).
- **FR-006**: Si el proveedor sugerido no coincide con ninguno del catálogo existente, el sistema
  DEBE ofrecerlo como propuesta de proveedor nuevo en vez de dejarlo vacío o descartar la
  sugerencia.
- **FR-007**: El sistema DEBE seguir permitiendo abrir y validar manualmente un documento para el
  que no pudo generar ninguna sugerencia, sin bloquear la revisión.
- **FR-008**: El sistema NO DEBE generar ni mostrar sugerencias para un documento que ya no está
  en REVISIÓN MANUAL.

### Key Entities

- **Sugerencia de Validación**: valores propuestos (proveedor sugerido, fecha sugerida, número
  sugerido, total sugerido) para un Documento Candidato, junto con si cada campo tuvo confianza
  suficiente para mostrarse; no es una decisión ni un dato confirmado, solo una ayuda visible
  mientras el documento sigue en REVISIÓN MANUAL.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Al menos el 70% de los documentos cuyo adjunto contiene datos identificables
  muestran una sugerencia precargada para los cuatro campos.
- **SC-002**: El tiempo medio para validar y archivar un documento con sugerencias precargadas es
  al menos un 30% menor que el tiempo de referencia sin sugerencias (specs/002-validacion-archivado-facturas/spec.md SC-001: menos de 2 minutos).
- **SC-003**: El 100% de los documentos archivados tienen registrada la persona que confirmó sus
  datos, sean estos sugeridos, corregidos o escritos desde cero — sin distinción de trazabilidad.
- **SC-004**: El 0% de los documentos se archivan sin que una persona autorizada haya confirmado
  explícitamente el archivado, incluso cuando todos los campos sugeridos tenían alta confianza.

## Assumptions

- Esta feature depende de specs/001-ingesta-facturas-email/ (el documento y su contenido) y de
  specs/002-validacion-archivado-facturas/ (el formulario de validación y la confirmación
  humana); no sustituye ninguna de las reglas de esas dos features, solo añade una precarga sobre
  el mismo formulario.
- El umbral de confianza a partir del cual se muestra o se omite un campo es un detalle técnico
  que se decidirá en el plan de esta feature, no en esta especificación.
- Las sugerencias se generan cuando el documento pasa a REVISIÓN MANUAL (reutilizando el mismo
  análisis de contenido que ya existe para clasificarlo, dentro del límite de una llamada por
  documento del Principio VII de la constitution) — no se recalculan cada vez que se abre la
  pantalla, ni se generan sugerencias nuevas para documentos que llevaban tiempo en REVISIÓN
  MANUAL antes de que esta feature existiera; esos documentos simplemente muestran el formulario
  vacío, como hoy.
- No se contempla en esta feature una reevaluación retroactiva de documentos ya existentes en
  REVISIÓN MANUAL: la sugerencia solo aplica a partir de que la feature esté activa.
