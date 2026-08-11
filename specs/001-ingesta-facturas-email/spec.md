# Feature Specification: Ingesta y Detección de Facturas por Email

**Feature Branch**: `001-ingesta-facturas-email`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "Conectar una cuenta de correo (Gmail/IMAP/Graph), detectar qué correos contienen facturas de gasto y extraer los adjuntos candidatos — el punto de entrada natural del producto."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conectar una cuenta de correo (Priority: P1)

La persona autorizada conecta su cuenta de correo (Gmail, IMAP genérico o Microsoft Graph) desde la aplicación para que el sistema pueda leer los correos entrantes en busca de facturas de gasto.

**Why this priority**: Sin una cuenta conectada no existe ningún dato que ingerir; es el requisito previo de todo el producto.

**Independent Test**: Puede probarse conectando una cuenta de prueba y verificando que la aplicación confirma la conexión y muestra el estado "conectada", sin necesidad de que ninguna otra funcionalidad exista todavía.

**Acceptance Scenarios**:

1. **Given** una persona autorizada ha iniciado sesión, **When** proporciona las credenciales/autorización de una cuenta de correo soportada, **Then** el sistema confirma la conexión y la deja disponible para iniciar una sincronización.
2. **Given** una cuenta de correo ya conectada, **When** las credenciales dejan de ser válidas (p. ej. token revocado), **Then** el sistema muestra el estado "desconectada" y solicita reconectar antes de poder sincronizar de nuevo.

---

### User Story 2 - Escanear el correo y detectar facturas candidatas (Priority: P1)

La persona autorizada inicia manualmente una sincronización y el sistema revisa los correos de la cuenta conectada, identificando cuáles parecen contener una factura de gasto y extrayendo sus adjuntos como documentos candidatos.

**Why this priority**: Es el valor central de la feature: convertir una bandeja de entrada en una lista de candidatos a revisar.

**Independent Test**: Puede probarse ejecutando una sincronización manual sobre una cuenta con correos de prueba (algunos con factura, otros sin ella) y comprobando que solo los relevantes aparecen como candidatos, con su adjunto disponible.

**Acceptance Scenarios**:

1. **Given** una cuenta conectada con correos nuevos desde la última sincronización, **When** la persona autorizada pulsa "sincronizar", **Then** el sistema procesa esos correos y añade un documento candidato por cada adjunto que parezca una factura de gasto.
2. **Given** un correo sin ningún adjunto o con adjuntos no relacionados con facturación, **When** se sincroniza, **Then** el sistema no genera ningún candidato para ese correo.
3. **Given** un correo que contiene una factura emitida por el propio usuario (factura de venta), **When** se sincroniza, **Then** el documento se clasifica como FACTURA DE VENTA y no se mezcla con los candidatos de gasto.
4. **Given** un correo que ya fue ingerido en una sincronización anterior (mismo mensaje), **When** se vuelve a sincronizar, **Then** el sistema lo reconoce como DUPLICADO IGNORADO y no crea un nuevo candidato.

---

### User Story 3 - Revisar la lista de candidatos detectados (Priority: P2)

La persona autorizada consulta la lista de documentos candidatos generados por la sincronización, con su estado y el enlace al correo/adjunto original, antes de que continúen hacia la fase de validación.

**Why this priority**: Da visibilidad y confianza sobre lo que el sistema ha detectado; sin esto la ingesta sería una caja negra.

**Independent Test**: Puede probarse tras una sincronización, listando los documentos candidatos y verificando que cada uno enlaza a su correo/adjunto original y muestra su estado (REVISIÓN MANUAL, NO ES FACTURA, FACTURA DE VENTA o DUPLICADO IGNORADO).

**Acceptance Scenarios**:

1. **Given** una sincronización ha finalizado, **When** la persona autorizada abre la lista de candidatos, **Then** ve cada documento con su estado, el remitente, la fecha del correo y el adjunto original accesible.
2. **Given** un documento candidato en estado REVISIÓN MANUAL, **When** la persona autorizada lo abre, **Then** puede ver el correo y adjunto originales sin que estos hayan sido modificados o movidos.

---

### Edge Cases

- ¿Qué ocurre si un correo tiene varios adjuntos y solo uno es una factura? → Solo el adjunto identificado como factura genera un documento candidato; el resto se ignora sin eliminarse del correo.
- ¿Qué ocurre si la cuenta de correo se desconecta a mitad de una sincronización? → La sincronización se detiene, los candidatos ya procesados hasta ese punto se conservan, y el resto de correos pendientes se procesará en la siguiente sincronización manual.
- ¿Qué ocurre si el sistema no puede determinar con confianza si un correo contiene una factura? → Se clasifica como REVISIÓN MANUAL por defecto en lugar de descartarlo, para que una persona decida.
- ¿Qué ocurre si dos correos distintos contienen el mismo adjunto de factura (reenvío)? → Ambos se ingieren como candidatos independientes; la detección de duplicado por contenido de factura (no por correo) es responsabilidad de la fase de validación, no de esta feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE exigir que la persona tenga una identidad autorizada activa antes de conectar una cuenta de correo o ver cualquier dato ingerido.
- **FR-002**: El sistema DEBE permitir conectar una cuenta de correo mediante Gmail, IMAP genérico o Microsoft Graph.
- **FR-003**: El sistema DEBE mostrar el estado de la conexión (conectada / desconectada / requiere reautorización) en todo momento.
- **FR-004**: El sistema DEBE iniciar cada sincronización únicamente por acción explícita de la persona autorizada; no debe existir sincronización automática ni programada.
- **FR-005**: El sistema DEBE identificar, dentro de los correos sincronizados, cuáles contienen probablemente una factura de gasto, basándose en su adjunto y contenido.
- **FR-006**: El sistema DEBE extraer como documento candidato cada adjunto identificado como posible factura de gasto, conservando el correo y el adjunto original sin modificarlos ni eliminarlos.
- **FR-007**: El sistema DEBE clasificar cada documento candidato en uno de los estados: REVISIÓN MANUAL, NO ES FACTURA, FACTURA DE VENTA o DUPLICADO IGNORADO. Ningún documento candidato de esta feature puede quedar en estado PROCESADA, ya que esa transición requiere la validación de la feature de validación y archivado.
- **FR-008**: El sistema DEBE marcar como REVISIÓN MANUAL cualquier correo para el que no pueda determinar con confianza suficiente si contiene o no una factura de gasto, en lugar de descartarlo silenciosamente.
- **FR-009**: El sistema DEBE reconocer un correo ya ingerido en una sincronización previa (mismo mensaje) y marcarlo como DUPLICADO IGNORADO en lugar de crear un nuevo candidato.
- **FR-010**: El sistema DEBE permitir a la persona autorizada consultar la lista de documentos candidatos con su estado, remitente, fecha y acceso al correo/adjunto original.
- **FR-011**: El sistema NO DEBE realizar ninguna escritura masiva ni cambio de estado hacia PROCESADA como resultado de la ingesta; su única salida es la lista de candidatos clasificados pendientes de la fase de validación.
- **FR-012**: El sistema DEBE registrar la fecha/hora de cada sincronización manual y qué persona autorizada la inició.

### Key Entities

- **Cuenta de Correo Conectada**: representa la conexión entre el sistema y una bandeja de entrada (Gmail, IMAP o Microsoft Graph); tiene un estado (conectada, desconectada, requiere reautorización) y pertenece a una persona autorizada.
- **Sincronización**: representa una ejecución manual de escaneo de correos; tiene fecha/hora de inicio, quién la inició y el rango de correos revisado.
- **Documento Candidato**: representa un adjunto extraído de un correo que ha sido clasificado como REVISIÓN MANUAL, NO ES FACTURA, FACTURA DE VENTA o DUPLICADO IGNORADO; enlaza al correo y adjunto originales sin copiarlos ni alterarlos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tras conectar una cuenta de correo, la persona autorizada puede ver su primera lista de documentos candidatos en menos de 5 minutos.
- **SC-002**: Al menos el 90% de los correos que contienen una factura de gasto real con adjunto quedan clasificados como candidato pendiente de revisión, en lugar de perderse silenciosamente.
- **SC-003**: Ningún correo o adjunto original resulta modificado o eliminado tras cualquier número de sincronizaciones, verificable comparando el correo en el proveedor de email antes y después.
- **SC-004**: El sistema procesa una sincronización de 100 correos nuevos en menos de 2 minutos.
- **SC-005**: Volver a sincronizar el mismo correo dos veces produce cero documentos candidatos duplicados adicionales.

## Assumptions

- La cuenta de correo conectada para ingesta es independiente de la cuenta de identidad autorizada usada para iniciar sesión en la aplicación (p. ej. isleca@protonmail.com puede iniciar sesión en la app y, por separado, conectar un buzón distinto donde llegan las facturas).
- Los formatos de adjunto soportados para detección de factura son PDF e imágenes habituales (JPG, PNG); una factura cuyos datos aparezcan únicamente en el cuerpo del correo, sin adjunto, queda fuera de alcance de esta primera versión.
- La ventana de importación al conectar una cuenta por primera vez cubre los correos de los últimos 90 días; las sincronizaciones posteriores solo cubren correos nuevos desde la última sincronización.
- El sistema admite conectar una única cuenta de correo por persona autorizada en esta primera versión; conectar varias cuentas queda fuera de alcance.
- La clasificación de un correo como "probable factura de gasto" no requiere confirmación humana en el momento de la ingesta; la ingesta solo determina si un documento merece pasar a revisión, y esa revisión ocurre en la fase de validación y archivado (fuera de esta feature).
