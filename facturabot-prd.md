# PRD — FacturaBot: Asistente de Facturas por Correo para Microempresas

**Versión:** 1.0  
**Fecha:** Julio 2026  
**Estado:** Borrador  
**Audiencia:** Fundador / Builder (vibe coding)

---

## Problema

Los propietarios de microempresas reciben facturas de proveedores mezcladas en su bandeja de entrada junto con newsletters, notificaciones y comunicaciones diversas. No existe una forma sistemática de separarlas: el proceso típico es buscar manualmente, descargar PDFs uno a uno y reenviarlos a contabilidad o a su gestor. Esto consume entre 3 y 8 horas al mes en una tarea repetitiva, propensa a errores y sin valor estratégico.

El coste de no resolverlo es doble: tiempo perdido que podría dedicarse al negocio, y facturas que se pierden o llegan tarde al gestor, generando problemas fiscales o multas.

---

## Objetivos

1. **Reducir en ≥ 50% el tiempo mensual** que los usuarios dedican a gestionar facturas por correo (de ~5 h/mes a ≤ 2,5 h/mes), medido mediante encuesta in-app a los 30 días.
2. **Lograr una tasa de activación ≥ 60%**: usuarios que completan la conexión de correo (OAuth o regla de reenvío) y ven sus primeras facturas detectadas en las primeras 24 horas.
3. **Detectar con precisión ≥ 85%** los correos que contienen facturas (PDFs adjuntos, cuerpos con importes y número de factura), medido contra un conjunto de prueba etiquetado manualmente.
4. **Retener ≥ 50% de usuarios activos** en el día 30 tras la activación, definido como usuarios que revisaron el panel al menos una vez durante la semana 4.
5. **Mantener la confianza del usuario**: 0 incidentes reportados de acceso indebido a datos fuera del alcance autorizado.

---

## No-Goals (v1)

| No hacemos | Por qué |
|---|---|
| Contabilidad automática o integración contable (Holded, Xero, QuickBooks) | Complejidad alta, requiere validación fiscal por país. Es v2. |
| OCR avanzado y extracción de campos (importe, proveedor, fecha) para exportar a CSV | El valor principal en v1 es separar el ruido, no procesar datos. Es v2. |
| App móvil nativa (iOS / Android) | Una web responsive cubre el caso de uso. Mobile-first es v2. |
| Soporte multi-idioma | El mercado inicial es hispanohablante. Inglés es v2. |
| Gestión de facturas emitidas (las que el usuario manda a sus clientes) | Hipótesis distinta. No está validada. Fuera de scope. |

---

## Usuarios Objetivo

### Persona principal: "María, gestora de su propia tienda"

- **Quién:** Propietaria de una microempresa (1-5 personas). Comercio, consultoría, servicio, hostelería.
- **Contexto:** No tiene departamento de administración. Ella misma lleva las facturas.
- **Dolor:** Busca "factura" en Gmail una vez al mes antes de mandársela todo al gestor. Siempre se le escapa alguna.
- **Nivel técnico:** Medio-bajo. Usa Google Workspace o Outlook. Sabe crear reglas de correo si alguien se lo explica paso a paso.
- **Motivación para cambiar:** El dolor de tiempo es real. Desconfía de apps que "leen todo su correo" pero aceptaría algo transparente con acceso limitado.

### Persona secundaria: "Carlos, autónomo freelance"

- **Quién:** Desarrollador, diseñador o consultor independiente. Solo.
- **Contexto:** Recibe facturas de herramientas SaaS (Figma, Notion, AWS), agencias y clientes.
- **Dolor:** Las facturas llegan en PDF desde emails automáticos y se mezclan con notificaciones. Las necesita para la declaración trimestral.
- **Nivel técnico:** Alto. Preferirá OAuth sobre regla de reenvío.

---

## Historias de Usuario

### Onboarding

- Como **nueva usuaria**, quiero conectar mi cuenta de Gmail u Outlook en menos de 3 clics, para no tener que configurar nada técnico y empezar a ver mis facturas de inmediato.
- Como **nueva usuaria con dudas de privacidad**, quiero ver claramente qué permisos pide la app y para qué se usan, para decidir con confianza si conectar mi correo.
- Como **usuaria que prefiere no dar acceso OAuth**, quiero recibir una dirección de correo especial a la que puedo reenviar facturas o crear una regla automática de reenvío, para usar la app sin conectar mi cuenta principal.

### Panel de facturas

- Como **usuaria activa**, quiero ver en un panel todas las facturas detectadas en los últimos 30 días, organizadas por fecha, para tener una vista consolidada sin entrar al correo.
- Como **usuaria activa**, quiero descargar todas las facturas del mes en un ZIP con un solo clic, para enviárselo fácilmente a mi gestor.
- Como **usuaria activa**, quiero poder marcar una factura como "irrelevante" o "falso positivo", para limpiar el panel y mejorar la detección.
- Como **usuaria activa**, quiero buscar facturas por nombre de proveedor o rango de fechas, para encontrar una factura concreta sin scrollear.

### Detección y clasificación

- Como **usuaria**, quiero que el sistema detecte automáticamente correos con facturas adjuntas (PDF, imagen) y los separe de los correos normales, para no tener que hacerlo manualmente.
- Como **usuaria**, quiero que la app también detecte facturas en el cuerpo del correo (sin adjunto), como las de Stripe, Apple o servicios SaaS, para no perder ninguna.

### Notificaciones

- Como **usuaria**, quiero recibir un resumen semanal por email con las facturas detectadas esa semana, para mantenerme al día sin tener que recordar entrar al panel.
- Como **usuaria**, quiero recibir una alerta si no se han detectado facturas en los últimos 15 días (periodo inusualmente largo), para verificar que la conexión sigue activa.

### Privacidad y control

- Como **usuaria preocupada por la privacidad**, quiero poder revocar el acceso a mi correo desde la app en cualquier momento, para tener control total sobre mis datos.
- Como **usuaria**, quiero que la app solo acceda a los correos relevantes (con PDF adjunto o palabras clave como "factura", "invoice", "recibo"), y no lea el resto de mi bandeja de entrada.

---

## Requisitos

### Must-Have — P0 (sin esto no hay producto)

**Onboarding**
- [ ] Conexión OAuth con Gmail (Google Workspace y cuentas personales)
- [ ] Alternativa de onboarding por reenvío a dirección dedicada (`facturas+{userid}@facturabot.app`) con guía paso a paso para crear la regla en Gmail y Outlook
- [ ] Pantalla de permisos que explica en lenguaje simple qué accede la app y qué no
- [ ] Confirmación de activación: el usuario ve al menos 1 factura detectada antes de salir del onboarding

**Detección**
- [ ] Clasificación automática de correos entrantes usando IA (prompt sobre asunto + remitente + presencia de adjunto PDF)
- [ ] Soporte a PDFs adjuntos como tipo de factura primario
- [ ] Procesamiento de correos de los últimos 90 días al conectar (retroactivo inicial)

**Panel**
- [ ] Vista de lista de facturas detectadas con: fecha, remitente, asunto, miniatura/icono del adjunto
- [ ] Descarga individual de cada factura (PDF original)
- [ ] Descarga en ZIP de todas las facturas del período seleccionado
- [ ] Botón "Esto no es una factura" (feedback negativo) por ítem

**Infraestructura**
- [ ] URL pública con dominio propio y HTTPS
- [ ] Autenticación de usuarios (email + contraseña o magic link)
- [ ] Los archivos procesados se almacenan en el servidor solo durante el período activo de la cuenta

**Privacidad**
- [ ] Opción de revocar acceso OAuth desde la configuración
- [ ] Política de privacidad publicada y enlazada desde el onboarding

---

### Nice-to-Have — P1 (mejoran significativamente la experiencia)

- [ ] Conexión OAuth con Outlook / Microsoft 365
- [ ] Filtro y búsqueda en el panel (por remitente, fecha, palabra clave)
- [ ] Resumen semanal automatizado por email con listado de facturas detectadas
- [ ] Etiquetado manual de facturas (ej. "Q2 2026", "Proveedor X") para organización propia
- [ ] Vista previa del PDF en el panel sin descargar
- [ ] Indicador de confianza de detección ("alta probabilidad" / "revisar") para que el usuario calibre el sistema

---

### Future Considerations — P2 (diseñar para soportarlo, no construir ahora)

- Extracción de campos (importe, número de factura, proveedor, fecha) y exportación a CSV/Excel
- Integración directa con software contable (Holded, Contasimple, Xero)
- Detección de facturas duplicadas
- App móvil (PWA primero, luego nativa)
- Soporte multiusuario / equipos (compartir panel con gestor)
- Alertas de vencimiento de facturas periódicas (suscripciones no renovadas)

---

## Métricas de Éxito

### Indicadores tempranos (semanas 1-4 post-lanzamiento)

| Métrica | Objetivo mínimo | Objetivo stretch | Cómo medir |
|---|---|---|---|
| Tasa de activación | ≥ 60% de registrados completan conexión y ven ≥ 1 factura | ≥ 75% | Evento `first_invoice_seen` en analytics |
| Tiempo hasta primera factura detectada | ≤ 5 minutos desde registro | ≤ 2 minutos | Timestamp registro vs. timestamp primer evento |
| Precisión de detección (falsos positivos) | ≤ 15% de items marcados como "no es factura" | ≤ 8% | Ratio clicks en botón de rechazo / total detectadas |
| Tasa de completado onboarding | ≥ 70% de quienes inician completan todos los pasos | ≥ 85% | Funnel onboarding en analytics |

### Indicadores de impacto (mes 1-3)

| Métrica | Objetivo | Cómo medir |
|---|---|---|
| Reducción de tiempo percibida | ≥ 50% de usuarios reportan ahorro ≥ 50% | Encuesta in-app en día 30 |
| Retención día 30 | ≥ 50% de usuarios activan en semana 4 | Panel de cohortes |
| NPS inicial | ≥ 30 | Encuesta in-app en día 14 |
| Descargas de ZIP / usuario / mes | ≥ 1 (señal de uso real) | Evento `zip_downloaded` |

---

## Stack recomendado para Vibe Coding (sin programación)

> Esta sección guía al builder sobre qué herramientas usar para cada capa, manteniendo el requisito de URL pública y sin código manual.

| Capa | Herramienta sugerida | Alternativa |
|---|---|---|
| Frontend + lógica de app | **Lovable** o **Bolt.new** (generación de UI con IA) | Glide, Softr |
| Base de datos + autenticación | **Supabase** (PostgreSQL + Auth + Storage) | Firebase |
| Automatización + clasificación IA | **Make** (Integromat) + llamada a **OpenAI API** | Zapier + OpenAI |
| Conexión Gmail OAuth | Make / Zapier connector nativo de Gmail | n8n self-hosted |
| Email entrante (reenvío) | **Mailgun Inbound Routing** o **Postmark Inbound** | SendGrid Inbound Parse |
| Hosting / dominio | Vercel (frontend generado por Lovable/Bolt) | Netlify |
| Almacenamiento PDFs | Supabase Storage | Cloudflare R2 |
| Comunicaciones (resumen semanal) | Resend o Loops | Mailgun |

### Flujo técnico en Make (sin código)

```
Gmail Trigger (nuevo correo con adjunto PDF)
  → Filtro: asunto o remitente contiene palabras clave (factura, invoice, recibo, receipt)
  → OpenAI: "¿Es este correo una factura de proveedor? Responde solo sí/no."
  → Si sí: guardar adjunto en Supabase Storage + insertar registro en tabla `facturas`
  → Responder con ID de factura almacenada
```

---

## Preguntas Abiertas

| # | Pregunta | Responsable | Bloqueante |
|---|---|---|---|
| 1 | ¿El alcance OAuth de Gmail ("leer correos con etiqueta X") es suficiente para la detección, o necesitamos acceso completo a la bandeja? Acceso más limitado = más confianza del usuario. | Builder / Google OAuth docs | **Sí** (antes de onboarding) |
| 2 | ¿Cuánto tiempo guardamos los PDFs en Supabase Storage? ¿Los borramos al revocar acceso? Necesitamos definir política de retención. | Fundador | **Sí** (antes de lanzar) |
| 3 | ¿La detección retroactiva de 90 días puede generar costes de API elevados en usuarios con muchos correos? ¿Ponemos un límite (ej. 500 correos)? | Builder | No (se puede ajustar post-lanzamiento) |
| 4 | ¿El precio inicial es freemium (X facturas gratis/mes) o acceso completo gratis en beta? | Fundador | No (no afecta v1 MVP) |
| 5 | ¿Existe algún requisito legal en España/LATAM sobre almacenamiento de facturas de terceros que debamos considerar en la política de privacidad? | Asesor legal | No (pero documentar antes de escalar) |

---

## Consideraciones de Timeline

### Fase 0 — Validación técnica (semana 1)
- Confirmar que Make + Gmail OAuth + OpenAI puede detectar facturas de forma fiable en un flujo de prueba manual.
- Probar Mailgun Inbound como alternativa de reenvío.
- Decisión go/no-go sobre el stack antes de construir la UI.

### Fase 1 — MVP funcional (semanas 2-4)
- Onboarding OAuth Gmail + alternativa reenvío.
- Detección automática + panel básico con lista y descarga.
- URL pública con dominio propio.
- 5-10 usuarios beta invitados manualmente.

### Fase 2 — Iterar sobre retención (semanas 5-8)
- Resumen semanal por email.
- Búsqueda y filtros en el panel.
- Conexión Outlook.
- Medir activación y retención; ajustar precisión de detección.

### Fase 3 — Crecer (mes 3+)
- Landing page pública + registro abierto.
- Modelo de monetización activo.
- Roadmap basado en datos de uso.

---

## Criterios de Éxito del MVP

El MVP se considera validado cuando:

- [ ] Al menos 10 usuarios reales (no el fundador) completan el onboarding y ven sus propias facturas detectadas.
- [ ] Al menos 6 de esos 10 usuarios descargan un ZIP o una factura individual.
- [ ] La tasa de falsos positivos en producción es ≤ 20% (umbral relajado para MVP).
- [ ] Al menos 5 usuarios responden la encuesta del día 14 con NPS ≥ 7/10.
- [ ] Ningún usuario reporta haber visto accedidos correos fuera del alcance prometido.
