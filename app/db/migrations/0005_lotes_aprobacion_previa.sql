-- Migración 005: lotes con aprobación previa y reanudación
-- (specs/006-lotes-aprobacion-previa/data-model.md, research.md)
-- SQLite no permite ampliar un CHECK existente con ALTER TABLE: se recrea sync_runs con el
-- CHECK de estado ampliado (+ 'pendiente_aprobacion') y las dos columnas de resumen nuevas.
-- BEGIN/COMMIT explícitos desde el primer momento (lección de la revisión de código sobre
-- atomicidad de migraciones: 0001/0003/0004 no lo hacían y se corrigieron después).
-- A diferencia de la recreación de candidate_documents en la migración 0002 (sin tablas hijas
-- todavía en ese momento), sync_runs ya es referenciada por ingested_emails.primera_sincronizacion_id
-- desde la migración 0001: hay que desactivar temporalmente la comprobación de claves foráneas
-- para poder hacer DROP+RENAME sin que SQLite la bloquee (la comprobación solo puede activarse o
-- desactivarse fuera de una transacción, así que va antes de BEGIN y después de COMMIT). Los
-- valores de `id` se preservan exactamente al copiar las filas, así que las referencias
-- existentes en ingested_emails siguen siendo válidas al reactivarla.

PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

CREATE TABLE sync_runs_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuenta_id INTEGER NOT NULL REFERENCES mailbox_accounts (id),
    iniciada_por TEXT NOT NULL,
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT,
    estado TEXT NOT NULL CHECK (
        estado IN ('pendiente_aprobacion', 'en_curso', 'completada', 'interrumpida')
    ),
    correos_procesados INTEGER NOT NULL DEFAULT 0,
    candidatos_generados INTEGER NOT NULL DEFAULT 0,
    correos_nuevos_detectados INTEGER NOT NULL DEFAULT 0,
    correos_con_adjuntos_candidatos INTEGER NOT NULL DEFAULT 0
);

INSERT INTO sync_runs_new
    (id, cuenta_id, iniciada_por, fecha_inicio, fecha_fin, estado,
     correos_procesados, candidatos_generados)
SELECT id, cuenta_id, iniciada_por, fecha_inicio, fecha_fin, estado,
       correos_procesados, candidatos_generados
FROM sync_runs;

DROP TABLE sync_runs;
ALTER TABLE sync_runs_new RENAME TO sync_runs;

-- FR-005: como máximo un lote pendiente de aprobación O en ejecución por cuenta a la vez
-- (sustituye al índice de la feature 001, que solo cubría 'en_curso').
CREATE UNIQUE INDEX IF NOT EXISTS ux_sync_runs_one_activo_per_account
    ON sync_runs (cuenta_id)
    WHERE estado IN ('pendiente_aprobacion', 'en_curso');

-- Los correos ya ingeridos por sincronizaciones de features anteriores ya generaron sus
-- candidate_documents bajo el flujo antiguo: quedan como PROCESADO por defecto.
ALTER TABLE ingested_emails ADD COLUMN estado_procesamiento TEXT NOT NULL DEFAULT 'PROCESADO'
    CHECK (estado_procesamiento IN ('PENDIENTE', 'PROCESADO', 'FALLIDO'));
ALTER TABLE ingested_emails ADD COLUMN motivo_fallo TEXT;

-- Adjuntos ya guardados (attachment_store) pero todavía sin clasificar: solo existen mientras
-- su correo esté PENDIENTE o FALLIDO (data-model.md § AdjuntoPendiente).
CREATE TABLE IF NOT EXISTS pending_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    correo_id INTEGER NOT NULL REFERENCES ingested_emails (id),
    archivo_adjunto_ref TEXT NOT NULL,
    nombre_archivo_original TEXT NOT NULL,
    formato TEXT NOT NULL CHECK (formato IN ('pdf', 'jpg', 'png'))
);

CREATE INDEX IF NOT EXISTS ix_pending_attachments_correo ON pending_attachments (correo_id);

COMMIT;

PRAGMA foreign_keys = ON;
