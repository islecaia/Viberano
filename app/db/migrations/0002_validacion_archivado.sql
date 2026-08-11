-- Migración 002: catálogo de proveedores y validación/archivado de documentos candidatos
-- (specs/002-validacion-archivado-facturas/data-model.md, research.md §1-§5)
-- BEGIN/COMMIT explícitos: la recreación de candidate_documents (DROP + RENAME) debe aplicarse
-- de forma atómica, para no dejar la base de datos a medio migrar si algo falla a mitad.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    identificador_fiscal TEXT,
    activo INTEGER NOT NULL DEFAULT 1,
    fecha_alta TEXT NOT NULL
);

-- Unicidad por nombre normalizado (research.md §5): comparación exacta, sin espacios extra ni
-- distinción de mayúsculas/minúsculas.
CREATE UNIQUE INDEX IF NOT EXISTS ux_providers_nombre_normalizado
    ON providers (lower(trim(nombre)));

-- SQLite no permite ampliar un CHECK existente con ALTER TABLE: se recrea candidate_documents
-- con el CHECK de estado ampliado (+ PROCESADA) y las columnas nuevas de validación
-- (research.md §2-§3).
CREATE TABLE candidate_documents_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    correo_id INTEGER NOT NULL REFERENCES ingested_emails (id),
    archivo_adjunto_ref TEXT NOT NULL,
    nombre_archivo_original TEXT NOT NULL,
    formato TEXT NOT NULL CHECK (formato IN ('pdf', 'jpg', 'png')),
    estado TEXT NOT NULL CHECK (
        estado IN (
            'REVISIÓN MANUAL', 'NO ES FACTURA', 'FACTURA DE VENTA', 'DUPLICADO IGNORADO',
            'PROCESADA'
        )
    ),
    motivo_clasificacion TEXT NOT NULL,
    fecha_creacion TEXT NOT NULL,
    proveedor_id INTEGER REFERENCES providers (id),
    fecha_factura TEXT,
    numero_factura TEXT,
    total REAL,
    es_nota_credito INTEGER NOT NULL DEFAULT 0,
    validado_por TEXT,
    fecha_validacion TEXT
);

INSERT INTO candidate_documents_new
    (id, correo_id, archivo_adjunto_ref, nombre_archivo_original, formato, estado,
     motivo_clasificacion, fecha_creacion)
SELECT id, correo_id, archivo_adjunto_ref, nombre_archivo_original, formato, estado,
       motivo_clasificacion, fecha_creacion
FROM candidate_documents;

DROP TABLE candidate_documents;
ALTER TABLE candidate_documents_new RENAME TO candidate_documents;

CREATE INDEX IF NOT EXISTS ix_candidate_documents_correo ON candidate_documents (correo_id);
CREATE INDEX IF NOT EXISTS ix_candidate_documents_estado ON candidate_documents (estado);

-- FR-009 / data-model.md: nunca dos documentos PROCESADA con el mismo proveedor+fecha+número.
CREATE UNIQUE INDEX IF NOT EXISTS ux_candidate_documents_factura_procesada
    ON candidate_documents (proveedor_id, fecha_factura, numero_factura)
    WHERE estado = 'PROCESADA';

COMMIT;
