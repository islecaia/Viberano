-- Migración 003: columnas de sugerencia automática de datos de factura
-- (specs/003-sugerencia-datos-factura/data-model.md, research.md §4)
-- Solo ADD COLUMN nullable: no hace falta recrear la tabla (a diferencia de la migración 0002),
-- porque ningún CHECK existente se ve afectado.

ALTER TABLE candidate_documents ADD COLUMN sugerido_proveedor_nombre TEXT;
ALTER TABLE candidate_documents ADD COLUMN sugerido_fecha_factura TEXT;
ALTER TABLE candidate_documents ADD COLUMN sugerido_numero_factura TEXT;
ALTER TABLE candidate_documents ADD COLUMN sugerido_total REAL;
