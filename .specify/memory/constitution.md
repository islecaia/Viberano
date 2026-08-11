<!--
Sync Impact Report
Version change: N/A (plantilla sin rellenar) → 1.0.0
Principios modificados: N/A → añadidos I–VII (todos nuevos, ratificación inicial)
Secciones añadidas: Alcance y Contexto del Producto; Estados de Factura; Autenticación y Control
  de Acceso; Sistema de Diseño; Artefactos de Documentación del Producto; Governance
Secciones eliminadas: ninguna
TODOs pendientes: ninguno
-->

# Invoice Manager Constitution

## Core Principles

### I. No Invención de Datos (Zero Hallucination)
No se inventa ningún dato fiscal, proveedor, importe ni número de factura sin evidencia
acreditada. Todo dato extraído o mostrado DEBE ser trazable a un correo, adjunto o extracto
bancario concreto; si la evidencia es insuficiente, el sistema DEBE marcar el dato como incierto
en lugar de completarlo por inferencia.
**Rationale**: Un dato fiscal incorrecto puede tener consecuencias legales y económicas directas
para autónomos y microempresas; la fiabilidad del dato es el valor central del producto.

### II. Validación Obligatoria Antes de Archivar
Ningún documento se archiva automáticamente sin pasar por validación de proveedor activo, fecha,
número y total. La validación de estos cuatro campos es condición necesaria para cualquier
transición a estado PROCESADA.
**Rationale**: Evita archivar facturas incompletas, duplicadas o fraudulentas sin control.

### III. Inmutabilidad de Originales
Los correos y adjuntos originales nunca se modifican ni eliminan, independientemente del
resultado del procesamiento (incluidos los marcados como NO ES FACTURA o DUPLICADO IGNORADO).
**Rationale**: Los originales son la fuente de verdad legal y deben permanecer disponibles para
auditoría.

### IV. No Sobrescritura de Archivos
No se sobrescriben archivos existentes bajo ninguna circunstancia. Cualquier nueva versión de un
archivo se guarda como un artefacto adicional, nunca reemplazando al anterior.
**Rationale**: Previene la pérdida irreversible de evidencia documental.

### V. Control Humano Explícito (No Automatización)
No hay tareas programadas ni aprobaciones automáticas: una persona autorizada DEBE iniciar y
confirmar cada acción, en particular cualquier escritura masiva o cambio de estado de facturas.
**Rationale**: El coste de un error de archivado fiscal es alto; la revisión humana es la última
línea de defensa.

### VI. Precisión en Estados de Conciliación
Una factura sin coincidencia bancaria se registra como "no encontrada en el extracto", nunca
como "impagada". El sistema NO DEBE inferir el estado de pago a partir de la ausencia de
coincidencia.
**Rationale**: "Impagada" es una afirmación fuerte con implicaciones para proveedores y
contabilidad; la ausencia de evidencia no equivale a impago.

### VII. Uso Acotado de IA de Pago
El uso de APIs de IA de pago (p. ej. Anthropic API) SOLO está permitido para tareas de
extracción/clasificación de datos de facturas, dentro de límites de coste y volumen definidos y
documentados en el plan técnico de cada feature. Estas APIs NUNCA deciden ni ejecutan por sí
solas el archivado, la validación o cualquier escritura de datos — esa decisión sigue sujeta al
Principio V. Cualquier ampliación de su alcance de uso requiere una enmienda a esta constitution.
**Rationale**: El producto necesita capacidades de IA para procesar lenguaje natural en correos y
adjuntos, pero el coste y el riesgo de decisiones automatizadas deben permanecer acotados y
auditables.

## Alcance y Contexto del Producto

Invoice Manager es una herramienta web para que autónomos y microempresas identifiquen, validen
y archiven facturas de gasto recibidas por email, con revisión humana obligatoria antes de
cualquier escritura masiva.

- **Plataforma**: web app responsive (desktop y móvil). Sin app nativa. Sin modo offline.
- **Idioma del producto**: español (es).
- **Stack técnico**: Python 3.11+, FastAPI, SQLite, uv, Anthropic API (uso acotado según
  Principio VII), Gmail API / IMAP / Microsoft Graph para ingesta de correo.

## Estados de Factura

El conjunto canónico y exhaustivo de estados de procesamiento es:

- **PROCESADA** — validada (proveedor activo, fecha, número y total) y archivada.
- **REVISIÓN MANUAL** — requiere intervención humana antes de continuar.
- **DUPLICADO IGNORADO** — coincide con una factura ya procesada; no se archiva de nuevo.
- **NO ES FACTURA** — el documento/correo no es una factura de gasto.
- **FACTURA DE VENTA** — es una factura emitida por el propio usuario, no un gasto.

Cualquier estado adicional, o cambio de significado de los existentes, requiere una enmienda a
esta constitution.

## Autenticación y Control de Acceso

Se requiere identidad autorizada obligatoria antes de mostrar cualquier dato o ejecutar cualquier
acción. La cuenta inicial autorizada es `isleca@protonmail.com`. Añadir o revocar cuentas
autorizadas es una decisión que DEBE quedar registrada y trazable.

## Sistema de Diseño

- **Tipografía**: Montserrat, pesos 400/600/700.
- **Paleta**: blanco + azul primario `#0062FF`.
- **Componentes**: tarjetas con radio de 12px.
- **Navegación**: barra inferior con Facturas / Proveedores / Conciliación / Actividad.

Estos requisitos visuales son vinculantes para toda interfaz nueva; cualquier desviación debe
justificarse explícitamente en el plan de la funcionalidad correspondiente.

## Artefactos de Documentación del Producto

- La especificación funcional de cada feature sigue la convención de Spec Kit: `spec.md` dentro
  de `specs/<NNN-feature-name>/`.
- El sistema de diseño visual (ver sección anterior) se documenta y mantiene en `DESIGN.md` en la
  raíz del proyecto; su creación queda como acción pendiente (ver Next Actions del informe de
  este comando).

## Governance

Esta constitution prevalece sobre cualquier otra práctica, plantilla o preferencia individual
dentro del proyecto. Toda spec, plan o conjunto de tareas que entre en conflicto con un principio
marcado como no negociable DEBE resolverse ajustando la spec/plan/tasks, nunca diluyendo el
principio.

- **Procedimiento de enmienda**: cualquier cambio a este documento requiere actualizar la
  versión (semver), registrar un Sync Impact Report al inicio del archivo, y justificar el
  motivo del cambio.
- **Política de versionado**: MAJOR para eliminación o redefinición incompatible de principios;
  MINOR para principios o secciones nuevas; PATCH para aclaraciones de redacción sin cambio
  semántico.
- **Revisión de cumplimiento**: `/speckit-analyze` y `/speckit-converge` DEBEN tratar cualquier
  violación de un principio "MUST"/"DEBE" como hallazgo CRITICAL. `/speckit-implement` no debe
  proceder sobre un hallazgo CRITICAL sin resolución explícita.

**Version**: 1.0.0 | **Ratified**: 2026-08-11 | **Last Amended**: 2026-08-11
