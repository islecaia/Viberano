# Quickstart: Lotes con Aprobación Previa y Reanudación

**Spec**: [spec.md](./spec.md) · **Contratos**: [contracts/api.md](./contracts/api.md) ·
**Modelo de datos**: [data-model.md](./data-model.md)

Requiere una cuenta de correo conectada (feature 001) con correos nuevos disponibles.

## Escenario 1 — Analizar muestra el resumen sin crear candidatos (User Story 1)

1. Con 3 correos nuevos en el buzón (2 con un PDF adjunto, 1 sin adjuntos), `POST
   /api/mailbox-accounts/{id}/sync`.
2. **Resultado esperado**: `202 Accepted`, `estado: "pendiente_aprobacion"`,
   `correos_nuevos_detectados: 3`, `correos_con_adjuntos_candidatos: 2`. `GET
   /api/candidate-documents` no muestra ningún documento nuevo todavía.

## Escenario 2 — Aprobar el lote crea los documentos candidato (User Story 1)

1. Sobre el lote del Escenario 1, `POST
   /api/mailbox-accounts/{id}/sync/{sync_run_id}/execute`.
2. **Resultado esperado**: `estado: "completada"`, `candidatos_generados: 2` (uno por correo con
   adjunto candidato); `GET /api/candidate-documents` ya los muestra en `REVISIÓN MANUAL` (o el
   estado que determine la clasificación).

## Escenario 3 — Un fallo en un correo no bloquea el resto del lote (User Story 3)

1. Analizar un lote con 3 correos con adjunto, simulando que el procesamiento del segundo falla
   (p. ej. un adjunto ilegible que provoca un error inesperado al guardarlo).
2. `POST .../execute`.
3. **Resultado esperado**: `correos_procesados: 3`, `candidatos_generados: 2` (los otros dos se
   guardaron), `correos_fallidos` contiene el correo 2 con su `motivo_fallo`; `estado:
   "completada"` (no `"interrumpida"` — un fallo de correo no es un fallo sistémico).

## Escenario 4 — Reintentar un correo fallido (User Story 3)

1. Sobre el resultado del Escenario 3, corregir la causa del fallo (o simplemente reintentar) y
   `POST .../execute` de nuevo sobre el mismo `sync_run_id`.
2. **Resultado esperado**: el correo que antes falló pasa a `PROCESADO`, `candidatos_generados`
   aumenta, y `correos_fallidos` ya no lo incluye; los correos ya procesados en el intento
   anterior no se vuelven a procesar (`correos_procesados` no los cuenta dos veces).

## Escenario 5 — No se puede analizar un lote nuevo con uno pendiente (FR-005)

1. Con un lote `pendiente_aprobacion` sin aprobar todavía, `POST /api/mailbox-accounts/{id}/sync`
   de nuevo para la misma cuenta.
2. **Resultado esperado**: `409 Conflict`.

## Validación de principios no negociables

- **Principio V**: analizar y ejecutar (aprobar/reanudar/reintentar) son siempre acciones
  explícitas — ningún lote se aprueba ni se ejecuta solo, y el Escenario 1 demuestra que analizar
  por sí solo no crea nada todavía.
- **Principio VII**: el Escenario 1 demuestra que la clasificación (la única llamada a la
  Anthropic API) no ocurre hasta que el lote se aprueba explícitamente en el Escenario 2.
