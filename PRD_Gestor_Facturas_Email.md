# PRD — Gestor Automatizado de Facturas por Email

> **Product Requirements Document · MVP v1.0**  
> Fecha: 16 de julio de 2026

---

## Tabla de contenidos

1. [Declaración del Problema](#1-declaración-del-problema)
2. [Objetivos](#2-objetivos)
3. [No Objetivos](#3-no-objetivos-fuera-de-alcance-en-v1)
4. [Historias de Usuario](#4-historias-de-usuario)
5. [Requisitos](#5-requisitos)
6. [Métricas de Éxito](#6-métricas-de-éxito)
7. [Preguntas Abiertas](#7-preguntas-abiertas)
8. [Timeline](#8-timeline)

---

## 1. Declaración del Problema

Las microempresas y tiendas individuales reciben el 99 % de sus facturas de forma digital en el correo electrónico, mezcladas con presupuestos, recibos, newsletters y comunicaciones genéricas. Revisar manualmente cientos de correos para extraer, clasificar y remitir facturas a la asesoría contable consume varias horas semanales y es propenso a errores u omisiones.

El impacto directo es un proceso de conciliación bancaria lento, riesgo de pérdida de facturas deducibles y un coste de tiempo desproporcionado para negocios con recursos limitados. Si no se resuelve, los propietarios seguirán invirtiendo tiempo operativo en tareas repetitivas que podrían automatizarse, reduciendo su capacidad de enfocarse en el negocio.

---

## 2. Objetivos

- Reducir el tiempo dedicado a la gestión manual de facturas en al menos un **80 %** en los primeros 30 días tras la activación.
- Lograr una tasa de clasificación automática correcta **≥ 90 %** en facturas de proveedores configurados.
- Que el **100 %** de las facturas identificadas queden disponibles en Google Drive y reflejadas en el Excel de exportación en menos de **5 minutos** desde la recepción del correo.
- Reducir las facturas perdidas u omitidas a **0** mediante la carpeta de "Revisión de Manager" para documentos no reconocidos.
- Que el producto sea utilizado activamente por al menos el **70 %** de los usuarios que completan el onboarding al cabo del primer mes.

---

## 3. No Objetivos (fuera de alcance en v1)

| No objetivo | Razón |
|---|---|
| **Contabilidad o ERP integrado** | La app extrae y organiza; no realiza asientos contables ni se conecta a software como Holded o Sage. |
| **Generación de facturas** | El sistema es de entrada (recepción), no de emisión. |
| **Canales distintos del email** | WhatsApp, SMS, portales de proveedores o facturas en papel quedan fuera de v1. |
| **Aprobación o flujo de pagos** | La app no gestiona órdenes de pago ni validaciones financieras. |
| **Multi-empresa** | v1 se centra en una única cuenta de email / empresa; la gestión multi-entidad es roadmap posterior. |

---

## 4. Historias de Usuario

### 4.1 Propietario / Administrador

- Como propietario, quiero **dar de alta proveedores con sus palabras clave** (p. ej. "Orange" + "FAC") para que el sistema identifique automáticamente sus facturas sin que yo tenga que revisar cada correo.
- Como propietario, quiero que las facturas detectadas **se envíen a una carpeta de Google Drive** predefinida para poder acceder a ellas desde cualquier dispositivo sin descargas manuales.
- Como propietario, quiero recibir un **Excel con los datos extraídos** de todas las facturas del período para enviarlo directamente a mi asesoría sin recopilación manual.
- Como propietario, quiero que los documentos no reconocidos vayan a una **carpeta de "Revisión de Manager"** para poder revisarlos cuando tenga tiempo sin riesgo de perderlos.
- Como propietario, quiero que la app **distinga entre facturas, presupuestos y recibos** para que solo se procese lo relevante para contabilidad.

### 4.2 Asesor Contable (usuario secundario)

- Como asesor, quiero recibir o acceder a un **Excel periódico** con todas las facturas del cliente para hacer la conciliación bancaria sin solicitar documentos uno a uno.
- Como asesor, quiero que las facturas incluyan los **metadatos clave** (proveedor, importe, fecha, número de factura) para no tener que abrir cada PDF manualmente.

### 4.3 Casos de error / excepción

- Como propietario, cuando una factura llega en un **idioma no configurado** (francés, inglés), quiero que el sistema aún pueda identificarla correctamente por palabras clave para no perder documentos internacionales.
- Como propietario, cuando el sistema **no puede clasificar un documento**, quiero que quede en "Revisión de Manager" con el correo original accesible para poder clasificarlo yo mismo.

---

## 5. Requisitos

### 5.1 Must-Have — P0

#### Conexión con cuenta de email (IMAP / OAuth)
La app debe autenticarse con la cuenta de correo del usuario y leer los mensajes entrantes en tiempo real o con polling frecuente (≤ 5 min).

**Criterio de aceptación:**
- [ ] Dado un correo nuevo con factura adjunta, cuando llega al inbox, entonces la app lo procesa en menos de 5 minutos.

#### Configuración de proveedores y palabras clave
Interfaz para dar de alta proveedores con nombre, palabras clave en asunto/cuerpo y tipo de documento esperado.

**Criterio de aceptación:**
- [ ] Un proveedor configurado con la palabra clave "FAC" es identificado correctamente en ≥ 90 % de sus correos.

#### Clasificación automática factura / presupuesto / recibo
El sistema distingue el tipo de documento y solo procesa facturas.

**Criterio de aceptación:**
- [ ] Los presupuestos y recibos no se suben a Drive ni aparecen en el Excel.

#### Exportación automática a Google Drive
Los PDFs de facturas se suben a una carpeta configurada por el usuario en Drive.

**Criterios de aceptación:**
- [ ] El archivo aparece en Drive en menos de 5 min.
- [ ] Conserva el nombre original o uno estandarizado (proveedor + fecha + número).

#### Generación de Excel con metadatos
Tras cada lote de procesamiento se actualiza un archivo `.xlsx` con columnas: Fecha, Proveedor, Número de factura, Importe, Moneda, Idioma, Ruta en Drive.

**Criterio de aceptación:**
- [ ] El Excel se actualiza con cada nueva factura procesada sin sobrescribir las anteriores.

#### Carpeta de Revisión de Manager
Documentos no reconocidos se mueven a una carpeta especial (Drive o local) con el adjunto original y el correo de origen.

**Criterio de aceptación:**
- [ ] Ningún documento entrante se pierde — o se clasifica correctamente o termina en Revisión de Manager.

---

### 5.2 Nice-to-Have — P1

- **Soporte multilingüe mejorado:** detección automática de idioma (FR, EN, ES) y extracción de campos en cada idioma sin configuración manual.
- **Notificaciones:** aviso por email o push cuando hay documentos en "Revisión de Manager" con más de 24 h sin revisar.
- **Dashboard básico:** resumen mensual de facturas procesadas, importe total, proveedores activos y documentos pendientes de revisión.
- **Reglas de enrutamiento:** enviar facturas de ciertos proveedores a subcarpetas específicas en Drive.

---

### 5.3 Consideraciones futuras — P2

- OCR avanzado para facturas escaneadas o en imagen (no PDF nativo).
- Integración con software de contabilidad (Holded, Sage, Xero) vía API.
- Soporte multi-empresa / multi-cuenta de email.
- Módulo de aprobación con firma digital para facturas de alto importe.

---

## 6. Métricas de Éxito

### 6.1 Indicadores líderes (semanas 1–4)

| Métrica | Definición | Objetivo |
|---|---|---|
| Tasa de activación | % de usuarios que procesan ≥ 1 factura en los primeros 7 días | ≥ 70 % |
| Tasa de clasificación correcta | Facturas identificadas correctamente / total recibidas de proveedores configurados | ≥ 90 % |
| Latencia de procesamiento | Tiempo entre recepción del email y aparición en Drive | p95 < 5 min |
| Tasa de excepciones | % de documentos enviados a "Revisión de Manager" | < 10 % |

### 6.2 Indicadores rezagados (meses 1–3)

| Métrica | Definición | Objetivo |
|---|---|---|
| Retención a 30 días | % de usuarios activos al cabo de un mes | ≥ 65 % |
| Ahorro de tiempo declarado | % de usuarios que declaran ahorrar ≥ 2 h/semana (encuesta día 30) | ≥ 60 % |
| NPS a 60 días | Net Promoter Score | ≥ 40 |
| Reducción de soporte | Tickets sobre facturas perdidas vs. baseline | −50 % |

---

## 7. Preguntas Abiertas

| # | Pregunta | Responsable | ¿Bloqueante? |
|---|---|---|---|
| 1 | ¿IMAP o API nativa de Gmail / Outlook? Las APIs nativas ofrecen webhooks en tiempo real; IMAP es universal pero más lento. | Ingeniería | ✅ Sí |
| 2 | Extracción de datos de PDFs: ¿parser estándar (pdfplumber) o LLM? El LLM mejora la cobertura pero añade coste y latencia. | Ingeniería | ✅ Sí |
| 3 | ¿Cuál es el volumen típico de facturas por usuario/mes? Necesario para dimensionar límites de plan y costes. | Producto | ✅ Sí |
| 4 | ¿Se almacenan las facturas en los servidores de la app o solo se enrutan a Drive? Impacta en el cumplimiento del RGPD. | Legal | ✅ Sí |
| 5 | ¿Cómo se guía al usuario para conectar su email y configurar el primer proveedor? (asistente vs. configuración libre) | Diseño | ⬜ No |
| 6 | ¿Modelo de negocio: freemium por volumen, suscripción plana, o pago por empresa? | Producto | ⬜ No |

---

## 8. Timeline

### Fase 1 — MVP Core (semanas 1–6)

- [ ] Conexión email (Gmail OAuth prioritario) + lectura de adjuntos
- [ ] Configuración de proveedores y palabras clave
- [ ] Clasificación básica y subida a Google Drive
- [ ] Generación de Excel con metadatos
- [ ] Carpeta de Revisión de Manager

### Fase 2 — Mejoras de experiencia (semanas 7–10)

- [ ] Dashboard básico
- [ ] Soporte multilingüe mejorado (FR, EN)
- [ ] Notificaciones de documentos pendientes
- [ ] Soporte a Outlook / IMAP genérico

### Fase 3 — Escalabilidad (semanas 11+)

- [ ] Reglas de enrutamiento avanzadas
- [ ] OCR para documentos escaneados
- [ ] Exploración de integraciones contables

---

*Este documento es un PRD vivo — se actualizará conforme avance el descubrimiento técnico y de producto.*
