# Data Model: Ingesta y Detección de Facturas por Email

**Fase**: 1 — Design & Contracts
**Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

Todas las entidades viven en SQLite (M1). Ningún campo de este modelo permite sobrescribir o
eliminar un correo/adjunto original (Principios III y IV); las tablas solo referencian copias de
solo lectura de los adjuntos.

## CuentaCorreo (`mailbox_accounts`)

Representa la conexión entre el sistema y un buzón (User Story 1).

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer PK | |
| `persona_autorizada_id` | FK → `personas_autorizadas.id` | Dueña de la conexión |
| `proveedor` | enum(`gmail`, `imap`, `microsoft_graph`) | FR-002 |
| `email_address` | text | Buzón conectado (independiente del email de login) |
| `estado` | enum(`conectada`, `desconectada`, `requiere_reautorizacion`) | FR-003 |
| `credenciales_ref` | text | Referencia opaca al secreto (token/contraseña) en el almacén seguro; nunca texto plano en esta tabla |
| `fecha_conexion` | datetime | |
| `ultima_sincronizacion_cursor` | datetime nullable | Marca de corte para la siguiente sync incremental |

**Validación**: `estado` solo puede transicionar `conectada → requiere_reautorizacion → conectada`
o `conectada → desconectada`; nunca se borra un registro existente al reconectar (se actualiza el
`estado` y `credenciales_ref`).

## Sincronizacion (`sync_runs`)

Representa una ejecución manual de escaneo (User Story 2, FR-004, FR-012).

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer PK | |
| `cuenta_id` | FK → `mailbox_accounts.id` | |
| `iniciada_por` | FK → `personas_autorizadas.id` | FR-012 |
| `fecha_inicio` | datetime | |
| `fecha_fin` | datetime nullable | Null mientras `estado = en_curso` |
| `estado` | enum(`en_curso`, `completada`, `interrumpida`) | Edge case: desconexión a mitad de sync → `interrumpida` |
| `correos_procesados` | integer | Contador, para SC-004 |
| `candidatos_generados` | integer | Contador |

**Validación**: solo puede existir un `sync_run` en estado `en_curso` por `cuenta_id` a la vez
(FR-004 — inicio manual, no concurrente consigo mismo).

## CorreoIngerido (`ingested_emails`)

Representa un correo ya visto, usado para deduplicación (FR-009).

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer PK | |
| `cuenta_id` | FK → `mailbox_accounts.id` | |
| `proveedor_message_id` | text | Id nativo del proveedor (ver research.md §2) |
| `remitente` | text | |
| `asunto` | text | |
| `fecha_correo` | datetime | |
| `primera_sincronizacion_id` | FK → `sync_runs.id` | En qué sync se vio por primera vez |

**Validación**: `(cuenta_id, proveedor_message_id)` es único. Un intento de insertar un duplicado
no crea una fila nueva ni un `DocumentoCandidato` nuevo: la sincronización lo reconoce y lo cuenta
como `DUPLICADO IGNORADO` (FR-009) sin tocar la fila existente.

## DocumentoCandidato (`candidate_documents`)

Representa un adjunto extraído, clasificado (User Story 2 y 3, FR-005 a FR-011).

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer PK | |
| `correo_id` | FK → `ingested_emails.id` | |
| `archivo_adjunto_ref` | text | Ruta de solo lectura al adjunto copiado (research.md §3); nunca apunta al original en el buzón |
| `nombre_archivo_original` | text | Solo metadato, no afecta a la ruta de almacenamiento |
| `formato` | enum(`pdf`, `jpg`, `png`) | Filtro de FR-005 |
| `estado` | enum(`REVISIÓN MANUAL`, `NO ES FACTURA`, `FACTURA DE VENTA`, `DUPLICADO IGNORADO`) | Nunca `PROCESADA` en esta feature (FR-007, FR-011) |
| `motivo_clasificacion` | text | Explicación breve (salida de clasificación o "duplicado de correo X") — trazabilidad para Principio I |
| `fecha_creacion` | datetime | |

**Validación**:
- `estado` es de solo estos 4 valores en esta feature; una transición a `PROCESADA` solo puede
  ocurrir en una feature futura de validación, nunca aquí (gate de Constitution Check, Principio
  II).
- Ante fallo o baja confianza de la clasificación (research.md §4), `estado` se fija a
  `REVISIÓN MANUAL`, nunca se omite la fila ni se asume `NO ES FACTURA`.
- `archivo_adjunto_ref` es inmutable tras la creación de la fila (no hay operación de update sobre
  ese campo en el dominio de esta feature).

## Relaciones

```
personas_autorizadas 1──* mailbox_accounts 1──* sync_runs
mailbox_accounts 1──* ingested_emails 1──* candidate_documents
sync_runs 1──* ingested_emails (primera_sincronizacion_id)
```

## Máquina de estados de `DocumentoCandidato` (alcance de esta feature)

```
(creación tras sync) ──▶ REVISIÓN MANUAL
                     ──▶ NO ES FACTURA
                     ──▶ FACTURA DE VENTA
                     ──▶ DUPLICADO IGNORADO

Cualquier otra transición (p. ej. REVISIÓN MANUAL → PROCESADA) queda fuera de esta feature;
pertenece a la futura feature de "Validación y archivado con revisión humana".
```
