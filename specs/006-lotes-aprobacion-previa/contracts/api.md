# API Contract: Lotes con Aprobación Previa y Reanudación

**Fase**: 1 — Design & Contracts
**Spec**: [spec.md](../spec.md) · **Data model**: [data-model.md](../data-model.md)

Todos los endpoints requieren sesión de persona autorizada activa (heredado de las features
anteriores).

## POST /api/mailbox-accounts/{id}/sync — ampliado (ahora "analizar")

Ya no ejecuta la sincronización completa: analiza el buzón y, solo si encuentra al menos un
correo con adjunto candidato, guarda esos correos y sus adjuntos (sin clasificarlos) y deja el
lote `pendiente_aprobacion` (User Story 1, FR-001 a FR-003). Si el análisis no encuentra ningún
correo con adjunto candidato, no se crea ningún registro de lote (FR-013) — la respuesta lo
indica con `"lote": null`, y la cuenta queda libre de inmediato para una nueva sincronización.

**Response `202 Accepted`** — con lote:

```json
{
  "lote": {
    "id": 5,
    "estado": "pendiente_aprobacion",
    "fecha_inicio": "2026-08-12T10:00:00Z",
    "fecha_fin": null,
    "correos_procesados": 0,
    "candidatos_generados": 0,
    "correos_nuevos_detectados": 12,
    "correos_con_adjuntos_candidatos": 7,
    "correos_fallidos": []
  }
}
```

**Response `202 Accepted`** — sin nada que revisar (FR-013):

```json
{ "lote": null }
```

**Errores**:
- `409 Conflict`: ya existe un lote de esta cuenta `pendiente_aprobacion` o `en_curso` (FR-005).
- `409 Conflict`: la cuenta no está conectada (sin cambios respecto a la feature 001).
- `502 Bad Gateway`: fallo de conexión con el proveedor de correo durante el análisis — no se
  crea ningún lote (igual que el caso de "nada que revisar", la cuenta queda libre para
  reintentar de inmediato).

---

## POST /api/mailbox-accounts/{id}/sync/{sync_run_id}/execute — nuevo

Procesa (clasifica y crea los documentos candidato de) todos los `ingested_emails` de este lote
en estado `PENDIENTE` o `FALLIDO`. Sirve indistintamente para aprobar un lote recién analizado,
reanudarlo tras una interrupción, o reintentar sus correos fallidos (User Stories 1, 2 y 3;
research.md §5) — el comportamiento es el mismo en los tres casos.

**Request**: sin cuerpo.

**Response `200 OK`**:

```json
{
  "id": 5,
  "estado": "completada",
  "fecha_inicio": "2026-08-12T10:00:00Z",
  "fecha_fin": "2026-08-12T10:02:00Z",
  "correos_procesados": 12,
  "candidatos_generados": 9,
  "correos_nuevos_detectados": 12,
  "correos_con_adjuntos_candidatos": 7,
  "correos_fallidos": [
    { "id": 88, "remitente": "...", "asunto": "...", "motivo_fallo": "..." }
  ]
}
```

- `estado: "completada"`: terminó de procesar todo lo que tenía `PENDIENTE`/`FALLIDO` (puede
  incluir correos fallidos en `correos_fallidos` — "completada" no implica cero fallos, FR-009).
- `estado: "interrumpida"`: un fallo sistémico (no de un correo concreto) detuvo la ejecución;
  puede volver a llamarse a este mismo endpoint para reanudar (FR-007).

**Errores**:
- `404 Not Found`: el lote no existe o no pertenece a la cuenta de la persona autorizada.
- `422 Unprocessable Entity`: no queda ningún correo `PENDIENTE` ni `FALLIDO` en este lote (nada
  que ejecutar o reintentar).

---

## GET /api/sync-runs/{id} — ampliado

**Response `200 OK`**: mismos campos que la respuesta de `execute` de más arriba (incluye
`correos_nuevos_detectados`, `correos_con_adjuntos_candidatos` y `correos_fallidos`).

**Errores**: `404 Not Found` (sin cambios).

---

## Sin cambios

Ningún endpoint de las features 001-005 cambia su comportamiento salvo el `POST .../sync`
descrito arriba (ahora "analiza" en vez de ejecutar la sincronización completa de una vez).
