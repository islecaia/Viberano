# Data Model: Lotes con Aprobación Previa y Reanudación

**Fase**: 1 — Design & Contracts
**Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

Se aplica vía `app/db/migrations/0005_lotes_aprobacion_previa.sql`: recrea `sync_runs`, amplía
`ingested_emails` con `ADD COLUMN`, y crea la tabla nueva `pending_attachments`.

## Sincronizacion / Lote (`sync_runs`) — tabla recreada (amplía la de la feature 001)

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer PK | |
| `cuenta_id` | integer, FK → `mailbox_accounts.id` | |
| `iniciada_por` | text | |
| `fecha_inicio` | datetime | Momento en que se inició el análisis |
| `fecha_fin` | datetime nullable | Se rellena al terminar la ejecución (`completada`/`interrumpida`) |
| `estado` | text | `'pendiente_aprobacion'` (nuevo), `'en_curso'`, `'completada'`, `'interrumpida'` |
| `correos_procesados` | integer | Correos cuyo procesamiento se intentó durante la ejecución (éxito o fallo) |
| `candidatos_generados` | integer | Documentos candidato creados |
| `correos_nuevos_detectados` | integer, nuevo | Calculado al terminar el análisis (FR-002) |
| `correos_con_adjuntos_candidatos` | integer, nuevo | Calculado al terminar el análisis (FR-002) |

**Máquina de estados**:

```
(inicio) ──(analizar)──────────────────────▶ pendiente_aprobacion
pendiente_aprobacion ──(execute, sin fallo sistémico)───▶ completada
pendiente_aprobacion ──(execute, fallo sistémico)───────▶ interrumpida
interrumpida ──(execute de nuevo)───────────▶ completada | interrumpida
completada ──(execute, solo si hay FALLIDO)─▶ completada   [reintento]

completada e interrumpida no son necesariamente finales: mientras existan ingested_emails de
ese lote en PENDIENTE o FALLIDO, `execute` puede volver a invocarse (research.md §5).
```

**Índice único parcial (ampliado, FR-005)**: como máximo un `sync_run` por `cuenta_id` con
`estado IN ('pendiente_aprobacion', 'en_curso')` — sustituye al índice de la feature 001 que solo
cubría `'en_curso'`.

## CorreoIngerido (`ingested_emails`) — columnas nuevas

| Campo nuevo | Tipo | Notas |
|---|---|---|
| `estado_procesamiento` | text | `'PENDIENTE'` (recién analizado), `'PROCESADO'` (candidatos creados), `'FALLIDO'` (ver `motivo_fallo`). Los correos de sincronizaciones anteriores a esta feature quedan `'PROCESADO'` por defecto (ya generaron sus candidatos bajo el flujo anterior). |
| `motivo_fallo` | text nullable | Motivo del último fallo; se limpia (`NULL`) al reintentar con éxito |

## AdjuntoPendiente (`pending_attachments`) — tabla nueva

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer PK | |
| `correo_id` | integer, FK → `ingested_emails.id` | |
| `archivo_adjunto_ref` | text | Misma referencia de solo lectura que usa `candidate_documents` (`attachment_store`) |
| `nombre_archivo_original` | text | |
| `formato` | text | `'pdf' \| 'jpg' \| 'png'` |

**Ciclo de vida**: se crea una fila por adjunto candidato durante el análisis (research.md §1); al
ejecutar con éxito, se convierte en un `candidate_documents` (misma `archivo_adjunto_ref`, sin
volver a guardar el archivo) y la fila de `pending_attachments` se elimina. Si el correo falla,
sus filas de `pending_attachments` se conservan intactas para el reintento.

## Relaciones

```
mailbox_accounts 1──* sync_runs (cuenta_id)
sync_runs 1──* ingested_emails (primera_sincronizacion_id, ya existente desde la feature 001)
ingested_emails 1──* pending_attachments (correo_id) — solo mientras estado_procesamiento ∈ {PENDIENTE, FALLIDO}
ingested_emails 1──* candidate_documents (correo_id, ya existente) — solo tras estado_procesamiento = PROCESADO
```
