-- Migración 003: columnas de sugerencia automática de datos de factura
-- (specs/003-sugerencia-datos-factura/data-model.md, research.md §4)
-- Solo ADD COLUMN nullable: no hace falta recrear la tabla (a diferencia de la migración 0002),
-- porque ningún CHECK existente se ve afectado.
-- BEGIN/COMMIT explícitos (revisión de código): ALTER TABLE ADD COLUMN no es idempotente: si una
-- de las cuatro sentencias falla, las anteriores ya habrían quedado confirmadas sin la
-- envoltura, y el reintento del script completo en el siguiente arranque fallaría de forma
-- permanente con "duplicate column name" en la primera columna ya añadida.

BEGIN TRANSACTION;

ALTER TABLE candidate_documents ADD COLUMN sugerido_proveedor_nombre TEXT;
ALTER TABLE candidate_documents ADD COLUMN sugerido_fecha_factura TEXT;
ALTER TABLE candidate_documents ADD COLUMN sugerido_numero_factura TEXT;
ALTER TABLE candidate_documents ADD COLUMN sugerido_total REAL;

COMMIT;
