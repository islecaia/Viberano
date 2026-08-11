# API Contract: Ingesta y Detección de Facturas por Email

**Fase**: 1 — Design & Contracts
**Spec**: [spec.md](../spec.md) · **Data model**: [data-model.md](../data-model.md)

Todos los endpoints requieren una sesión de persona autorizada activa (FR-001). Sin sesión válida,
cualquier endpoint responde `401 Unauthorized` sin filtrar datos.

## POST /api/mailbox-accounts

Inicia la conexión de una cuenta de correo (User Story 1).

**Request**:
```json
{
  "proveedor": "gmail | imap | microsoft_graph",
  "email_address": "facturas@empresa.example",
  "credenciales": { "...": "según proveedor: token OAuth de retorno o usuario/contraseña IMAP" }
}
```

> Nota de implementación: `email_address` se añadió como campo explícito (en vez de asumirlo
> implícito dentro de `credenciales`) al escribir la ruta en T017, para que el modelo
> `CuentaCorreo` no dependa de la forma interna de `credenciales`, que varía por proveedor.

**Response `201 Created`**:
```json
{
  "id": 1,
  "proveedor": "imap",
  "email_address": "facturas@empresa.example",
  "estado": "conectada",
  "fecha_conexion": "2026-08-11T10:00:00Z"
}
```

**Errores**: `422` credenciales inválidas o proveedor no soportado; `409` ya existe una cuenta
conectada para esta persona autorizada (Assumption: una sola cuenta por usuario).

---

## GET /api/mailbox-accounts/current

Consulta el estado de la cuenta conectada de la persona autorizada actual (FR-003).

**Response `200 OK`**:
```json
{
  "id": 1,
  "proveedor": "imap",
  "email_address": "facturas@empresa.example",
  "estado": "conectada | desconectada | requiere_reautorizacion",
  "ultima_sincronizacion_cursor": "2026-08-10T09:00:00Z"
}
```

**Response `404 Not Found`**: ninguna cuenta conectada todavía.

---

## POST /api/mailbox-accounts/{id}/sync

Dispara manualmente una sincronización (User Story 2, FR-004). No existe ningún trigger
automático equivalente en el sistema.

**Response `202 Accepted`**:
```json
{ "sync_run_id": 42, "estado": "en_curso" }
```

**Errores**: `409` ya hay una sincronización `en_curso` para esta cuenta; `409` la cuenta está en
estado `requiere_reautorizacion` o `desconectada`.

---

## GET /api/sync-runs/{id}

Consulta el progreso/resultado de una sincronización (para reflejar SC-001, SC-004 en la UI).

**Response `200 OK`**:
```json
{
  "id": 42,
  "estado": "en_curso | completada | interrumpida",
  "fecha_inicio": "2026-08-11T10:05:00Z",
  "fecha_fin": null,
  "correos_procesados": 37,
  "candidatos_generados": 5
}
```

---

## GET /api/candidate-documents

Lista los documentos candidatos generados por las sincronizaciones (User Story 3, FR-010).

**Query params**: `estado` (opcional, uno de `REVISIÓN MANUAL`, `NO ES FACTURA`,
`FACTURA DE VENTA`, `DUPLICADO IGNORADO`), `desde`/`hasta` (rango de fecha de correo).

**Response `200 OK`**:
```json
{
  "items": [
    {
      "id": 501,
      "estado": "REVISIÓN MANUAL",
      "remitente": "proveedor@ejemplo.com",
      "asunto": "Factura agosto",
      "fecha_correo": "2026-08-09T08:30:00Z",
      "formato": "pdf",
      "nombre_archivo_original": "factura-agosto.pdf"
    }
  ],
  "total": 1
}
```

---

## GET /api/candidate-documents/{id}

Detalle de un documento candidato, con acceso de solo lectura al adjunto y al correo original
(User Story 3, acceptance scenario 2).

**Response `200 OK`**:
```json
{
  "id": 501,
  "estado": "REVISIÓN MANUAL",
  "motivo_clasificacion": "Adjunto PDF con estructura de factura; proveedor no verificado",
  "correo": {
    "remitente": "proveedor@ejemplo.com",
    "asunto": "Factura agosto",
    "fecha_correo": "2026-08-09T08:30:00Z"
  },
  "adjunto_url": "/api/candidate-documents/501/attachment"
}
```

## GET /api/candidate-documents/{id}/attachment

Devuelve el binario del adjunto original (solo lectura, sin transformación) para visualizarlo o
descargarlo desde la pantalla de revisión.

**Response**: `200 OK` con `Content-Type` según `formato` (`application/pdf`, `image/jpeg`,
`image/png`).

---

## Fuera de alcance de este contrato

Ningún endpoint de esta feature permite cambiar `estado` a `PROCESADA`, editar datos fiscales
extraídos, ni ejecutar una escritura masiva: esas acciones pertenecen a la futura feature de
validación y archivado (Principio II de la constitution).
