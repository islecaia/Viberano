# Research: Ingesta y Detección de Facturas por Email

**Fase**: 0 — Outline & Research
**Fecha**: 2026-08-11
**Spec**: [spec.md](./spec.md)

Todas las decisiones técnicas de esta feature vienen ya acotadas por el stack y las restricciones
indicadas en la invocación de `/speckit-plan`. Este documento consolida esas decisiones en formato
Decision/Rationale/Alternatives para dejar constancia de por qué se eligieron, y resuelve los
puntos que la spec dejó como Assumptions traduciéndolos a decisiones técnicas concretas.

## 1. Abstracción de proveedores de correo (Gmail / IMAP / Microsoft Graph)

- **Decision**: Definir una interfaz común `MailboxConnector` con métodos `connect()`,
  `list_new_messages(since)`, `get_attachment(message_id, attachment_id)`, implementada por tres
  adaptadores: `GmailConnector` (Gmail API, OAuth2), `ImapConnector` (IMAP genérico,
  usuario/contraseña o app password), `GraphConnector` (Microsoft Graph API, OAuth2). El resto del
  sistema (detección, clasificación, listado) solo conoce la interfaz, no el proveedor concreto.
- **Rationale**: FR-002 exige soportar los tres proveedores sin que el resto de la aplicación
  duplique lógica por proveedor; permite añadir un cuarto proveedor en el futuro sin tocar la
  capa de detección/clasificación.
- **Alternatives considered**: Integrar cada proveedor de forma ad-hoc en la capa de
  sincronización → descartado por duplicar la lógica de deduplicación y clasificación tres veces
  y dificultar el cumplimiento uniforme de "no modificar el original" (Principio III).

## 2. Identificación única de mensajes para deduplicación (FR-009)

- **Decision**: Usar el identificador nativo de cada proveedor (`id` de Gmail, header
  `Message-ID` en IMAP, `id` de Graph) como `proveedor_message_id`, único junto con `cuenta_id` en
  la tabla `correos_ingeridos`. Antes de crear un nuevo `DocumentoCandidato` para un mensaje, se
  comprueba si ese `(cuenta_id, proveedor_message_id)` ya existe.
- **Rationale**: Es el único identificador estable que no depende de heurísticas de contenido y
  que ya provee cada proveedor; evita falsos negativos de deduplicación por reenvíos con distinto
  asunto.
- **Alternatives considered**: Hash del contenido del adjunto → descartado como clave primaria de
  deduplicación de *correos* porque un mismo adjunto reenviado por dos correos distintos debe
  generar dos candidatos independientes según el edge case documentado en spec.md (la
  deduplicación por contenido de factura pertenece a la fase de validación, no a esta feature).

## 3. Almacenamiento de adjuntos originales (Principios III y IV)

- **Decision**: Cada adjunto candidato se copia una única vez a un almacén de solo lectura en
  disco, con nombre de archivo derivado de `(cuenta_id, proveedor_message_id, attachment_id)` —
  nunca del nombre original — de forma que un reintento de sincronización sobre el mismo mensaje
  nunca produce una escritura sobre un archivo ya existente (si el archivo destino ya existe, no
  se vuelve a escribir; se reutiliza la referencia). El correo y el adjunto en el buzón de origen
  nunca se tocan: solo se leen vía la API/protocolo del proveedor.
- **Rationale**: Cumple directamente el Principio III (inmutabilidad de originales) y el Principio
  IV (no sobrescritura), y hace que SC-003 y SC-005 sean verificables de forma determinista.
- **Alternatives considered**: Guardar el adjunto como BLOB en SQLite → descartado por volumen
  (adjuntos PDF/imagen) y porque complica servir el archivo original desde la pantalla de revisión
  (User Story 3) sin capas adicionales.

## 4. Detección y clasificación (Principios I, II, VII)

- **Decision**: Detección en dos pasos. (1) Filtro barato sin IA: un correo solo se considera para
  clasificación si tiene al menos un adjunto en formato PDF, JPG o PNG (ver Assumption de spec.md
  sobre formatos soportados). (2) Clasificación con la Anthropic API (modelo económico de la
  familia Claude, p. ej. Haiku) usando como entrada únicamente remitente, asunto y el texto
  extraído del adjunto (OCR/parseo de PDF ya realizado localmente, no el archivo binario completo),
  para producir una de tres salidas: "probable factura de gasto", "no es factura" o "factura de
  venta". Si la llamada falla, se agota el tiempo de espera, o la confianza devuelta está por
  debajo de un umbral, el documento se clasifica como REVISIÓN MANUAL por defecto (nunca se
  descarta ni se asume "no es factura").
- **Rationale**: Cumple el Principio VII (uso acotado: solo clasificación, nunca decide archivado)
  y el Principio I (ante duda, no se inventa una clasificación certera). El filtro previo sin IA
  acota el volumen de llamadas de pago al número de correos con adjunto relevante, no al total de
  correos sincronizados.
- **Límites de coste y volumen (requeridos por el Principio VII)**: máximo una llamada a la
  Anthropic API por adjunto candidato (nunca se reintenta automáticamente sin acción humana);
  el filtro de formato de archivo elimina de antemano los correos sin adjunto PDF/JPG/PNG: el
  volumen de llamadas de un sync queda acotado por `correos_procesados` de esa sincronización, no
  por el histórico completo del buzón. El modelo a usar (familia Claude, variante económica) y el
  presupuesto mensual concreto quedan como parámetro de configuración documentado en el `.env` de
  despliegue, fuera del alcance de este documento de research.
- **Alternatives considered**: Clasificar el correo completo (cuerpo + adjunto binario) en una
  sola llamada de mayor tamaño → descartado por coste y porque excede el alcance "extracción/
  clasificación" acotado del Principio VII si se le pidiera además decidir el archivado.

## 5. Sincronización manual, sin tareas programadas (Principio V)

- **Decision**: La sincronización se implementa como un endpoint HTTP que un humano dispara
  explícitamente (botón "Sincronizar" en la UI). No se incluye ningún scheduler (APScheduler,
  Celery beat, cron) en el stack de esta feature. Una sincronización en curso se modela como un
  registro `Sincronizacion` con estado `en_curso`, para que la UI pueda mostrar progreso y para
  que una desconexión a mitad de proceso dejo un estado `interrumpida` en vez de perderse (edge
  case de spec.md).
- **Rationale**: Cumple literalmente el Principio V ("no hay tareas programadas ni aprobaciones
  automáticas").
- **Alternatives considered**: Job en segundo plano disparado automáticamente al conectar la
  cuenta → descartado porque violaría el Principio V incluso si el disparo inicial fue manual.

## 6. Autenticación mínima de la persona autorizada

- **Decision**: Esta feature depende de una capa de autenticación mínima (sesión de servidor)
  que verifique que quien conecta el buzón y ve los candidatos es una identidad autorizada
  (inicialmente `isleca@protonmail.com`, según la constitution). Se incluye como parte del
  scaffold de M1, ya que es un prerrequisito duro de FR-001 y ningún otro milestone puede
  implementarse de forma verificable sin ella. No se diseña aquí un sistema de gestión de cuentas
  múltiples ni de roles — eso queda fuera de alcance de esta feature.
- **Rationale**: La constitution exige "identidad autorizada obligatoria antes de mostrar datos o
  ejecutar acciones"; sin esto, M2–M5 no se pueden validar de forma independiente como exige la
  spec.
- **Alternatives considered**: Aplazar la autenticación a una feature separada y dejar M2–M6 sin
  gate de acceso hasta entonces → descartado porque dejaría el sistema en violación del principio
  de auth durante todo el desarrollo de esta feature, incumpliendo el gate de constitution check.

## 7. Almacenamiento y concurrencia en SQLite

- **Decision**: SQLite en modo WAL (`PRAGMA journal_mode=WAL`), acceso desde FastAPI vía
  SQLAlchemy Core o `sqlite3` directo con una única conexión de escritura por proceso.
- **Rationale**: El volumen esperado (una persona, un buzón, cientos de correos/mes) no requiere
  una base de datos cliente-servidor; WAL evita bloqueos entre la lectura de la lista de
  candidatos y la escritura durante una sincronización en curso.
- **Alternatives considered**: PostgreSQL → descartado por el stack ya fijado en la constitution
  (SQLite explícito) y por ser sobre-ingeniería para el volumen y el modo de despliegue
  (self-hosted, single-tenant) de este producto.

## Resumen de resolución de Assumptions de spec.md

| Assumption en spec.md | Traducción técnica |
|---|---|
| Ventana de importación: 90 días | Primer sync de una cuenta recién conectada filtra mensajes con fecha ≥ hoy−90 días; syncs posteriores usan `ultima_sincronizacion.fecha_fin` como cursor incremental. |
| Formatos soportados: PDF, JPG, PNG | Filtro de adjunto por MIME type / extensión antes de invocar clasificación. |
| Una sola cuenta de correo por usuario | `mailbox_accounts` tiene una restricción única por `persona_autorizada_id` en esta versión (no un límite técnico duro, sino de producto — documentado, no forzado a nivel de esquema para no bloquear una futura ampliación). |

No quedan `NEEDS CLARIFICATION` pendientes en el Technical Context de plan.md.
