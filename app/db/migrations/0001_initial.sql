-- Esquema SQLite de la feature 001-ingesta-facturas-email (data-model.md)
-- Ningún campo de este esquema permite sobrescribir o eliminar un correo/adjunto original
-- (Principios III y IV de la constitution): las tablas solo referencian copias de solo lectura.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS mailbox_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_autorizada TEXT NOT NULL,
    proveedor TEXT NOT NULL CHECK (proveedor IN ('gmail', 'imap', 'microsoft_graph')),
    email_address TEXT NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('conectada', 'desconectada', 'requiere_reautorizacion')),
    credenciales_ref TEXT NOT NULL,
    fecha_conexion TEXT NOT NULL,
    ultima_sincronizacion_cursor TEXT,
    UNIQUE (persona_autorizada)
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuenta_id INTEGER NOT NULL REFERENCES mailbox_accounts (id),
    iniciada_por TEXT NOT NULL,
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT,
    estado TEXT NOT NULL CHECK (estado IN ('en_curso', 'completada', 'interrumpida')),
    correos_procesados INTEGER NOT NULL DEFAULT 0,
    candidatos_generados INTEGER NOT NULL DEFAULT 0
);

-- FR-004: solo una sincronización en_curso por cuenta a la vez.
CREATE UNIQUE INDEX IF NOT EXISTS ux_sync_runs_one_en_curso_per_account
    ON sync_runs (cuenta_id)
    WHERE estado = 'en_curso';

CREATE TABLE IF NOT EXISTS ingested_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuenta_id INTEGER NOT NULL REFERENCES mailbox_accounts (id),
    proveedor_message_id TEXT NOT NULL,
    remitente TEXT NOT NULL,
    asunto TEXT NOT NULL,
    fecha_correo TEXT NOT NULL,
    primera_sincronizacion_id INTEGER NOT NULL REFERENCES sync_runs (id),
    UNIQUE (cuenta_id, proveedor_message_id)
);

CREATE TABLE IF NOT EXISTS candidate_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    correo_id INTEGER NOT NULL REFERENCES ingested_emails (id),
    archivo_adjunto_ref TEXT NOT NULL,
    nombre_archivo_original TEXT NOT NULL,
    formato TEXT NOT NULL CHECK (formato IN ('pdf', 'jpg', 'png')),
    estado TEXT NOT NULL CHECK (
        estado IN ('REVISIÓN MANUAL', 'NO ES FACTURA', 'FACTURA DE VENTA', 'DUPLICADO IGNORADO')
    ),
    motivo_clasificacion TEXT NOT NULL,
    fecha_creacion TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_candidate_documents_correo ON candidate_documents (correo_id);
CREATE INDEX IF NOT EXISTS ix_candidate_documents_estado ON candidate_documents (estado);
