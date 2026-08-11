# Quickstart: Sugerencia Automática de Datos de Factura

**Spec**: [spec.md](./spec.md) · **Contratos**: [contracts/api.md](./contracts/api.md) ·
**Modelo de datos**: [data-model.md](./data-model.md)

Requiere `ANTHROPIC_API_KEY` configurada (feature 001) y al menos una sincronización que genere
un documento candidato con contenido identificable.

## Escenario 1 — Sugerencia precargada al validar (User Story 1)

1. Sincronizar un correo con un adjunto PDF que contenga claramente proveedor, fecha, número y
   total (por ejemplo, generado con `scripts/send_test_email.py` usando un PDF real de prueba).
2. `GET /api/candidate-documents/{id}` sobre el documento resultante en `REVISIÓN MANUAL`.
3. **Resultado esperado**: la respuesta incluye `sugerencia` con al menos algunos de los cuatro
   campos rellenos.
4. Abrir la pantalla de detalle del documento en `/facturas/{id}`.
5. **Resultado esperado**: el formulario de validación aparece con esos campos precargados y
   marcados visualmente como sugerencia.

## Escenario 2 — Campo sin confianza suficiente queda vacío (FR-003)

1. Sincronizar un correo con un adjunto PDF de baja calidad o con datos ambiguos (por ejemplo, el
   PDF en blanco de `scripts/send_test_email.py`, que no tiene texto extraíble).
2. `GET /api/candidate-documents/{id}`.
3. **Resultado esperado**: `sugerencia` es `null`, o tiene campos individuales en `null` — nunca
   un valor inventado.
4. Abrir la pantalla de detalle: el formulario se muestra igual que antes de esta feature (vacío
   en los campos sin sugerencia).

## Escenario 3 — Proveedor sugerido no existe en el catálogo (User Story 2)

1. Sincronizar un documento cuyo proveedor identificado no coincida con ninguno ya dado de alta.
2. `GET /api/candidate-documents/{id}` → `sugerencia.proveedor_id_coincidente` es `null`,
   `sugerencia.proveedor_nombre` tiene el nombre identificado.
3. Abrir la pantalla de detalle: el selector de proveedor debe mostrar la opción "proveedor
   nuevo" con ese nombre precargado, no un proveedor existente seleccionado.
4. Confirmar el archivado sin tocar el campo de proveedor.
5. **Resultado esperado**: se crea el proveedor nuevo y el documento pasa a `PROCESADA`, igual
   que si la persona hubiera escrito el nombre a mano (specs/002-validacion-archivado-facturas/quickstart.md Escenario 1).

## Escenario 4 — Corregir una sugerencia antes de confirmar (User Story 1, escenario 4)

1. Sobre el documento del Escenario 1, cambiar manualmente el total sugerido por otro valor en el
   formulario antes de confirmar.
2. `POST /api/candidate-documents/{id}/validate` con el valor corregido.
3. **Resultado esperado**: el documento se archiva con el valor corregido, no con el sugerido —
   `GET /api/candidate-documents/{id}` lo confirma.

## Validación de principios no negociables

- **Principio I**: en el Escenario 2, ante datos ambiguos, el sistema nunca completa un campo con
  una suposición — queda vacío.
- **Principio II/FR-005**: en ningún escenario un documento pasa a `PROCESADA` sin que
  `POST .../validate` se haya llamado explícitamente, incluso cuando todos los campos venían
  precargados con alta confianza (Escenario 3, paso 4-5).
- **Principio VII**: la generación de la sugerencia no añade ninguna llamada nueva a la Anthropic
  API — reutiliza la misma llamada de clasificación ya contabilizada en
  specs/001-ingesta-facturas-email/.
