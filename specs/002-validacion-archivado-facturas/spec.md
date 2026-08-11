# Feature Specification: Validación y Archivado con Revisión Humana

**Feature Branch**: `002-validacion-archivado-facturas`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "Validación y archivado con revisión humana: flujo por el cual una persona autorizada revisa los documentos candidatos en estado REVISIÓN MANUAL (generados por la feature de ingesta), valida que tengan proveedor activo, fecha, número de factura y total, y confirma explícitamente su archivado — momento en el que un documento pasa a estado PROCESADA. Ningún documento se archiva automáticamente sin esa validación de los cuatro campos y esa confirmación humana explícita. Incluye poder marcar un documento como NO ES FACTURA o FACTURA DE VENTA si la clasificación automática se equivocó, y ver el motivo por el que quedó en REVISIÓN MANUAL."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validar y archivar un documento candidato (Priority: P1) 🎯 MVP

Como persona autorizada, quiero introducir o confirmar el proveedor, la fecha, el número y el total de un documento candidato en REVISIÓN MANUAL, y confirmar explícitamente su archivado, para que solo pasen a PROCESADA los documentos que he verificado yo misma.

**Why this priority**: Es el propósito central de la feature — sin esto, los documentos candidatos de la feature de ingesta se acumulan en REVISIÓN MANUAL sin ningún camino hacia el archivo definitivo.

**Independent Test**: Puede probarse abriendo un documento en REVISIÓN MANUAL, rellenando los cuatro campos con un proveedor ya activo, confirmando el archivado, y comprobando que su estado pasa a PROCESADA con esos cuatro datos guardados.

**Acceptance Scenarios**:

1. **Given** un documento en REVISIÓN MANUAL y un proveedor activo, **When** la persona autorizada introduce proveedor, fecha, número y total, y confirma el archivado, **Then** el documento pasa a PROCESADA con esos cuatro datos asociados y con quién y cuándo lo confirmó.
2. **Given** un documento con algún campo vacío o no numérico en el total, **When** la persona intenta confirmar el archivado, **Then** el sistema lo impide y señala qué campo falta o es inválido, sin cambiar el estado del documento.
3. **Given** un documento cuyo proveedor introducido no figura como activo en el catálogo, **When** la persona intenta confirmar el archivado, **Then** el sistema lo impide y ofrece activar ese proveedor antes de continuar.
4. **Given** un documento ya validado y confirmado, **When** se consulta su registro, **Then** se puede ver quién lo archivó y cuándo, además de los cuatro campos.

---

### User Story 2 - Mantener un catálogo mínimo de proveedores activos (Priority: P1)

Como persona autorizada, quiero añadir proveedores y marcarlos como activos o inactivos, para que la validación de facturas tenga contra qué comprobar el proveedor.

**Why this priority**: User Story 1 depende de que exista al menos un proveedor activo contra el que validar; sin esta historia, ningún documento podría llegar nunca a PROCESADA.

**Independent Test**: Puede probarse añadiendo un proveedor nuevo, marcándolo activo, y comprobando que aparece disponible para validar facturas; luego marcándolo inactivo y comprobando que deja de aceptarse en nuevas validaciones.

**Acceptance Scenarios**:

1. **Given** ningún proveedor todavía registrado, **When** la persona autorizada añade uno con un nombre, **Then** queda disponible en el catálogo, activo por defecto.
2. **Given** un proveedor activo, **When** la persona autorizada lo marca como inactivo, **Then** deja de poder usarse para validar nuevos documentos, aunque los ya archivados con ese proveedor conservan su registro.
3. **Given** que la persona está validando un documento (User Story 1) y el proveedor que escribe no existe en el catálogo, **When** elige añadirlo desde esa misma pantalla, **Then** el proveedor se crea y queda activo sin salir del flujo de validación.

---

### User Story 3 - Corregir una clasificación automática equivocada (Priority: P2)

Como persona autorizada, quiero marcar un documento en REVISIÓN MANUAL como NO ES FACTURA o como FACTURA DE VENTA cuando compruebo que la clasificación automática se equivocó, sin tener que rellenar los cuatro campos de validación.

**Why this priority**: Da salida a los documentos que nunca deberían llegar a PROCESADA, evitando que se acumulen indefinidamente en REVISIÓN MANUAL solo porque no son facturas de gasto válidas.

**Independent Test**: Puede probarse abriendo un documento en REVISIÓN MANUAL que en realidad es un documento no relacionado con facturación, marcándolo como NO ES FACTURA, y comprobando que su estado cambia sin pedir proveedor/fecha/número/total.

**Acceptance Scenarios**:

1. **Given** un documento en REVISIÓN MANUAL que resulta no ser una factura, **When** la persona lo marca como NO ES FACTURA, **Then** su estado cambia a NO ES FACTURA sin exigir los cuatro campos de validación.
2. **Given** un documento en REVISIÓN MANUAL que resulta ser una factura emitida por el propio usuario, **When** la persona lo marca como FACTURA DE VENTA, **Then** su estado cambia a FACTURA DE VENTA sin exigir los cuatro campos de validación.
3. **Given** cualquier documento que se está revisando, **When** la persona autorizada consulta la pantalla de revisión, **Then** puede ver el motivo por el que la clasificación automática lo dejó en REVISIÓN MANUAL.

---

### Edge Cases

- ¿Qué ocurre si el nombre de archivo de destino del archivado ya existe (misma fecha, proveedor, número)? → El documento no se archiva sobre el existente; queda señalado para revisión en lugar de completarse el archivado, sin sobrescribir nada.
- ¿Qué ocurre si el total introducido es negativo? → Solo se acepta si la persona indica explícitamente que es una nota de crédito o abono; en cualquier otro caso se trata como dato inválido.
- ¿Qué ocurre si dos personas autorizadas intentan validar y archivar el mismo documento a la vez? → Solo la primera confirmación se aplica; la segunda persona ve que el documento ya no está en REVISIÓN MANUAL antes de poder confirmar.
- ¿Qué ocurre si se intenta reclasificar (User Story 3) un documento que ya no está en REVISIÓN MANUAL? → El sistema lo impide, ya que PROCESADA, NO ES FACTURA y FACTURA DE VENTA son estados finales dentro del alcance de esta feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir a la persona autorizada introducir o confirmar cuatro campos para un documento en REVISIÓN MANUAL: proveedor, fecha de factura, número de factura y total.
- **FR-002**: El sistema DEBE comprobar que el proveedor introducido figura como activo en el catálogo de proveedores antes de permitir el archivado.
- **FR-003**: El sistema NO DEBE transicionar ningún documento a PROCESADA si falta alguno de los cuatro campos, si el proveedor no está activo, o si no hay confirmación explícita de la persona autorizada.
- **FR-004**: El sistema DEBE transicionar un documento a PROCESADA únicamente en el momento en que la persona autorizada confirma explícitamente su archivado, nunca antes ni automáticamente.
- **FR-005**: El sistema DEBE permitir a la persona autorizada añadir un proveedor nuevo al catálogo (activo por defecto), incluyendo poder hacerlo sin abandonar la pantalla de validación de un documento.
- **FR-006**: El sistema DEBE permitir a la persona autorizada marcar y desmarcar un proveedor como activo en cualquier momento.
- **FR-007**: El sistema DEBE permitir a la persona autorizada reclasificar un documento en REVISIÓN MANUAL como NO ES FACTURA o FACTURA DE VENTA, sin exigir los cuatro campos de validación.
- **FR-008**: El sistema DEBE registrar qué persona autorizada confirmó el archivado de cada documento y en qué momento.
- **FR-009**: El sistema NO DEBE sobrescribir un archivo ya archivado con el mismo nombre de destino; ante esa colisión, el documento DEBE quedar señalado para revisión en lugar de completar el archivado.
- **FR-010**: El sistema DEBE mantener accesibles el correo y el adjunto originales, sin modificarlos, después de que un documento pase a PROCESADA.
- **FR-011**: El sistema NO DEBE permitir cambiar el estado de un documento que ya está en PROCESADA, NO ES FACTURA o FACTURA DE VENTA — dentro del alcance de esta feature son estados finales.
- **FR-012**: El sistema DEBE mostrar, para cualquier documento en revisión, el motivo por el que la clasificación automática lo dejó en REVISIÓN MANUAL (capacidad ya entregada por la feature de ingesta, reutilizada aquí).

### Key Entities

- **Proveedor**: nombre, identificador fiscal (opcional, solo si hay evidencia), estado (activo/inactivo), fecha de alta.
- **Validación de Documento**: ampliación del Documento Candidato de la feature de ingesta con proveedor asociado, fecha de factura, número de factura, total, quién confirmó el archivado y cuándo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una persona autorizada puede validar y archivar un documento candidato completo (con proveedor ya activo) en menos de 2 minutos.
- **SC-002**: El 100% de los documentos en estado PROCESADA tienen los cuatro campos (proveedor activo, fecha, número, total) completos.
- **SC-003**: El 100% de los documentos en estado PROCESADA tienen registrada la persona y el momento de la confirmación.
- **SC-004**: Ningún intento de archivado sobre un nombre de destino ya existente sobrescribe el archivo previo, verificable comparando el archivo antes y después del intento.
- **SC-005**: Añadir un proveedor nuevo y dejarlo activo, desde la pantalla de validación, tarda menos de 1 minuto.

## Assumptions

- Esta feature construye sobre la de ingesta (specs/001-ingesta-facturas-email): asume que ya existen documentos candidatos en REVISIÓN MANUAL, NO ES FACTURA o FACTURA DE VENTA, y que la pantalla de detalle con el motivo de clasificación y el adjunto original ya están disponibles.
- El catálogo de proveedores de esta feature es intencionadamente mínimo (nombre, identificador fiscal opcional, activo/inactivo): gestión más avanzada (edición completa, fusión de duplicados, exportación) queda fuera de alcance y se trataría como una feature futura.
- Si el proveedor introducido no está activo, la persona puede activarlo directamente desde la pantalla de validación en lugar de tener que ir primero a una pantalla de proveedores separada.
- Los documentos ya resueltos como NO ES FACTURA o FACTURA DE VENTA se consideran estados finales dentro de esta feature; reabrirlos o revertir una decisión queda fuera de alcance (podría añadirse en una feature futura si resulta necesario).
- El "archivado" de esta feature es la transición de estado a PROCESADA con los cuatro campos verificados; la organización de una copia legible del PDF (por ejemplo, en carpetas por año/trimestre/mes con un nombre descriptivo) es un detalle de implementación que se decidirá en el plan técnico, siempre respetando que nunca se sobrescribe un archivo existente (FR-009).
- DUPLICADO IGNORADO no forma parte del alcance de esta feature: la feature de ingesta no genera documentos candidatos en ese estado (los correos duplicados se descartan antes de crear un registro), por lo que no hay nada que validar ahí.
