-- Migración 004: conciliación bancaria
-- (specs/004-conciliacion-bancaria/data-model.md, research.md)
-- Solo ADD COLUMN nullable sobre candidate_documents: no hace falta recrear la tabla.
-- BEGIN/COMMIT explícitos (revisión de código): los ALTER TABLE ADD COLUMN de más abajo no son
-- idempotentes; sin esta envoltura, un fallo a mitad de script (p. ej. en la creación del índice
-- único) dejaría columnas ya añadidas y confirmadas sin registrar la migración como aplicada, y
-- el siguiente arranque reintentaría el script completo, fallando de forma permanente con
-- "duplicate column name".

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS bank_statements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT NOT NULL,
    aportado_por TEXT NOT NULL,
    fecha_aporte TEXT NOT NULL,
    total_movimientos INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS bank_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    extracto_id INTEGER NOT NULL REFERENCES bank_statements (id),
    fecha TEXT NOT NULL,
    importe REAL NOT NULL,
    concepto TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_bank_movements_extracto ON bank_movements (extracto_id);

ALTER TABLE candidate_documents ADD COLUMN estado_conciliacion TEXT
    CHECK (
        estado_conciliacion IN ('CONCILIADA', 'NO ENCONTRADA EN EXTRACTO', 'PENDIENTE REVISIÓN CONCILIACIÓN')
    );

ALTER TABLE candidate_documents ADD COLUMN movimiento_bancario_id INTEGER
    REFERENCES bank_movements (id);

-- Extracto que produjo el estado_conciliacion actual (incluida NO ENCONTRADA/PENDIENTE, que no
-- tienen un movimiento_bancario_id propio): necesario para que GET /api/reconciliations/{id}
-- pueda listar qué facturas evaluó cada extracto (contracts/api.md).
ALTER TABLE candidate_documents ADD COLUMN conciliado_con_extracto_id INTEGER
    REFERENCES bank_statements (id);

-- FR-006/Principio I: un movimiento bancario nunca queda vinculado a más de una factura
-- (múltiples NULL siguen permitidos: solo se exige unicidad entre los valores no nulos).
CREATE UNIQUE INDEX IF NOT EXISTS ux_candidate_documents_movimiento_bancario
    ON candidate_documents (movimiento_bancario_id);

CREATE TABLE IF NOT EXISTS reconciliation_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    documento_id INTEGER NOT NULL REFERENCES candidate_documents (id),
    movimiento_id INTEGER NOT NULL REFERENCES bank_movements (id)
);

CREATE INDEX IF NOT EXISTS ix_reconciliation_candidates_documento
    ON reconciliation_candidates (documento_id);

COMMIT;
