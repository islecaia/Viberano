# DESIGN.md — ReparaPRO · Gestión de Facturas de Gasto

**App**: ReparaPRO (módulo de administración)
**Plataforma**: Móvil (iOS y Android)
**Público**: Responsable de administración y responsable contable
**Idioma de la interfaz**: Español

---

## Principios de diseño

La app es una herramienta de trabajo interno para personas que gestionan documentación fiscal. El diseño prioriza **claridad sobre expresividad**, **precisión sobre decoración** y **seguridad visual sobre urgencia**. Todo elemento debe justificarse por su utilidad, no por su apariencia.

- **Confianza ante todo.** Los datos financieros y fiscales exigen una interfaz que transmita control y fiabilidad.
- **Densidad moderada.** La pantalla muestra listas largas de facturas y estados; se necesita jerarquía clara sin sobrecargar.
- **Acciones irreversibles, siempre confirmadas.** Aprobar un lote, desactivar un proveedor o archivar en masa requieren confirmación explícita.
- **Los estados son protagonistas.** `PROCESADA`, `REVISIÓN MANUAL`, `DUPLICADO IGNORADO`, `NO ES FACTURA` y `FACTURA DE VENTA` deben ser reconocibles de un vistazo.

---

## Paleta de colores

### Base

| Token                  | Hex       | Uso                                                  |
|------------------------|-----------|------------------------------------------------------|
| `color-bg`             | `#F8FAFC` | Fondo de pantalla                                    |
| `color-surface`        | `#FFFFFF` | Tarjetas, modales, bottom sheets                     |
| `color-surface-raised` | `#F1F5F9` | Fondos secundarios, filas alternas, secciones        |
| `color-border`         | `#E2E8F0` | Bordes de tarjeta, separadores, inputs sin foco      |
| `color-border-strong`  | `#CBD5E1` | Bordes de input con foco, divisores importantes      |

### Texto

| Token                  | Hex       | Uso                                                  |
|------------------------|-----------|------------------------------------------------------|
| `color-text-primary`   | `#0F172A` | Títulos, etiquetas principales, importes             |
| `color-text-secondary` | `#475569` | Metadatos, proveedor en lista, fechas                |
| `color-text-muted`     | `#94A3B8` | Placeholders, campos vacíos, texto deshabilitado     |
| `color-text-inverse`   | `#FFFFFF` | Texto sobre fondos de color primario o de estado     |

### Primario (marca)

| Token                  | Hex       | Uso                                                  |
|------------------------|-----------|------------------------------------------------------|
| `color-primary`        | `#1E40AF` | Botón primario, links, barra de navegación activa    |
| `color-primary-light`  | `#DBEAFE` | Fondo de estado informativo, tint de selección       |
| `color-primary-dark`   | `#1E3A8A` | Hover/pressed en botón primario                      |

> Azul profundo institucional. Transmite rigor y confianza sin ser opresivo.

### Estados de factura

Cada estado tiene un color de fondo `_bg`, un color de texto `_text` y un color de borde/icono `_accent` para usarse en chips, filas y banners.

| Estado                 | `_bg`     | `_text`   | `_accent` |
|------------------------|-----------|-----------|-----------|
| `PROCESADA`            | `#DCFCE7` | `#14532D` | `#16A34A` |
| `REVISIÓN MANUAL`      | `#FEF3C7` | `#78350F` | `#D97706` |
| `DUPLICADO IGNORADO`   | `#F3E8FF` | `#4C1D95` | `#7C3AED` |
| `NO ES FACTURA`        | `#F1F5F9` | `#334155` | `#64748B` |
| `FACTURA DE VENTA`     | `#E0F2FE` | `#0C4A6E` | `#0284C7` |

### Semánticos del sistema

| Token                  | Hex       | Uso                                                          |
|------------------------|-----------|--------------------------------------------------------------|
| `color-success`        | `#16A34A` | Confirmaciones, archivado correcto, conciliación encontrada  |
| `color-warning`        | `#D97706` | Advertencias, campos incompletos, revisiones pendientes      |
| `color-danger`         | `#DC2626` | Errores, acciones destructivas, datos contradictorios        |
| `color-danger-light`   | `#FEE2E2` | Fondo de banner de error                                     |
| `color-info`           | `#0284C7` | Información neutra, cobertura parcial, avisos de alcance     |

---

## Tipografía

**Familia principal**: Inter (disponible en Google Fonts y sistema iOS/Android a través de la fuente del sistema con fallback `system-ui, -apple-system, sans-serif`).

**Familia monoespaciada**: `JetBrains Mono` o `Roboto Mono` — exclusivamente para importes, números de factura, NIF/CIF y referencias bancarias.

### Escala tipográfica

| Token           | Tamaño | Peso      | Altura de línea | Uso                                          |
|-----------------|--------|-----------|-----------------|----------------------------------------------|
| `text-xs`       | 11px   | 400       | 16px            | Etiquetas de campo vacío, metadatos mínimos  |
| `text-sm`       | 13px   | 400 / 500 | 20px            | Metadatos de lista, fechas, estado secundario|
| `text-base`     | 15px   | 400       | 24px            | Cuerpo, descripciones, textos de formulario  |
| `text-md`       | 17px   | 500 / 600 | 24px            | Nombre del proveedor en lista, campo clave   |
| `text-lg`       | 20px   | 600       | 28px            | Título de pantalla, importe principal        |
| `text-xl`       | 24px   | 700       | 32px            | Total de factura en vista de detalle         |
| `text-display`  | 32px   | 700       | 40px            | Métricas resumen (facturas/mes, media)       |

**Importe en lista**: `text-md`, `font-mono`, alineado a la derecha, `color-text-primary`.
**Número de factura**: `text-sm`, `font-mono`, `color-text-secondary`.
**NIF/CIF**: `text-sm`, `font-mono`, `color-text-muted` si no acreditado.

---

## Espaciado

Sistema basado en múltiplos de **4px**.

| Token      | Valor | Uso típico                                              |
|------------|-------|---------------------------------------------------------|
| `space-1`  | 4px   | Separación mínima entre etiqueta e icono                |
| `space-2`  | 8px   | Padding interno de chip, separación entre metadatos     |
| `space-3`  | 12px  | Padding horizontal de input pequeño, gap entre iconos   |
| `space-4`  | 16px  | Padding estándar de tarjeta, margen lateral de pantalla |
| `space-5`  | 20px  | Separación entre secciones dentro de una tarjeta        |
| `space-6`  | 24px  | Separación entre grupos de campos en formulario         |
| `space-8`  | 32px  | Separación entre secciones de pantalla                  |
| `space-10` | 40px  | Margen superior de pantalla con título grande           |
| `space-12` | 48px  | Altura mínima de fila en lista                          |

**Margen lateral de pantalla**: `space-4` (16px) en todos los lados.
**Safe area inferior**: respetar siempre la safe area de iOS y Android para el botón de acción principal o la navegación.

---

## Esquinas (border-radius)

| Token            | Valor | Uso                                                        |
|------------------|-------|------------------------------------------------------------|
| `radius-xs`      | 4px   | Chips de estado muy pequeños, badges de recuento           |
| `radius-sm`      | 6px   | Chips de estado estándar, etiquetas de proveedor           |
| `radius-md`      | 8px   | Botones, inputs, fields de formulario                      |
| `radius-lg`      | 12px  | Tarjetas de factura, tarjetas de proveedor                 |
| `radius-xl`      | 16px  | Bottom sheets, modales de confirmación (esquinas superiores)|
| `radius-full`    | 9999px| Avatares de inicial de proveedor, indicadores de progreso  |

Sin esquinas completamente cuadradas ni completamente redondas en elementos funcionales. El radio `md` (8px) es el estándar por defecto.

---

## Botones

### Variantes

**Primario** — acción principal de la pantalla (ej. "Aprobar lote", "Guardar proveedor")
- Fondo: `color-primary`
- Texto: `color-text-inverse`, `text-md`, weight 600
- Radio: `radius-md`
- Padding: `12px space-4` (12px vertical, 16px horizontal)
- Altura mínima: 48px
- Estado pressed: `color-primary-dark`
- Estado deshabilitado: `color-border-strong` con texto `color-text-muted`

**Secundario** — acción complementaria (ej. "Cancelar", "Ver detalle")
- Fondo: transparente
- Borde: 1.5px `color-border-strong`
- Texto: `color-text-primary`, `text-md`, weight 500
- Resto igual al primario

**Destructivo** — acción irreversible (ej. "Desactivar proveedor", "Descartar lote")
- Fondo: `color-danger`
- Texto: `color-text-inverse`
- Siempre acompañado de un modal de confirmación antes de ejecutarse

**Ghost** — acciones en lista o dentro de tarjetas (ej. "Ver factura", "Abrir correo")
- Sin fondo ni borde
- Texto: `color-primary`, `text-sm`, weight 500
- Padding mínimo, altura mínima de tap target 44px

**Botón de acción flotante (FAB)** — no se usa en esta app. Las acciones primarias se ubican en el contexto de cada pantalla.

### Tamaños

| Tamaño  | Altura | Uso                                         |
|---------|--------|---------------------------------------------|
| `sm`    | 36px   | Acciones dentro de tarjetas o filas de lista|
| `md`    | 48px   | Botón estándar de pantalla                  |
| `lg`    | 56px   | Botón único de acción en bottom bar         |

---

## Inputs y formularios

- **Altura**: 48px
- **Borde en reposo**: 1px `color-border`
- **Borde con foco**: 2px `color-primary`
- **Borde con error**: 2px `color-danger`
- **Radio**: `radius-md` (8px)
- **Texto**: `text-base`, `color-text-primary`
- **Placeholder**: `text-base`, `color-text-muted`
- **Label**: `text-sm`, weight 500, `color-text-secondary`, 6px encima del input
- **Mensaje de error**: `text-sm`, `color-danger`, 4px debajo del input

Los campos de solo lectura (NIF extraído, número de factura detectado) usan fondo `color-surface-raised` y texto `color-text-secondary` para diferenciarlos visualmente de los editables.

---

## Chips de estado

Usados en listas de facturas, resúmenes de lote y detalle de documento.

```
[● PROCESADA]   fondo: #DCFCE7   texto: #14532D   punto: #16A34A
[● REVISIÓN MANUAL]   fondo: #FEF3C7   texto: #78350F   punto: #D97706
[● DUPLICADO IGNORADO]   fondo: #F3E8FF   texto: #4C1D95   punto: #7C3AED
[● NO ES FACTURA]   fondo: #F1F5F9   texto: #334155   punto: #64748B
[● FACTURA DE VENTA]   fondo: #E0F2FE   texto: #0C4A6E   punto: #0284C7
```

- Radio: `radius-sm` (6px)
- Padding: `4px 8px`
- Texto: `text-xs`, weight 600, mayúsculas preservadas tal como están en el spec
- Punto de color: 6px de diámetro, `radius-full`, a la izquierda del texto

---

## Sombras y elevación

Sistema de tres niveles. Usar con moderación — la mayoría de la interfaz es plana.

| Nivel | CSS box-shadow                                       | Uso                              |
|-------|------------------------------------------------------|----------------------------------|
| `sm`  | `0 1px 2px rgba(15,23,42,0.06)`                     | Tarjetas en lista                |
| `md`  | `0 4px 12px rgba(15,23,42,0.10)`                    | Bottom sheet, modal              |
| `lg`  | `0 8px 24px rgba(15,23,42,0.14)`                    | Diálogos de confirmación crítica |

---

## Tono de los textos

### Principios

- **Directo y sin ambigüedad.** El responsable de administración maneja datos fiscales; no necesita suavizantes ni entusiasmo.
- **Verbos en infinitivo** para acciones: "Aprobar", "Archivar", "Revisar", no "¡Guarda tu factura!".
- **Sin signos de exclamación** salvo error crítico o acción completada con impacto alto.
- **Oraciones cortas.** Si una frase supera las 12 palabras, se parte.
- **Los estados son mayúsculas fijas** tal como aparecen en el spec: `PROCESADA`, `REVISIÓN MANUAL`, etc. No se traducen ni se adaptan.

### Ejemplos por contexto

**Títulos de pantalla**
- Facturas de gasto
- Detalle de factura
- Proveedores activos
- Conciliación bancaria
- Actividad del lote

**Etiquetas de campo**
- Proveedor
- N.º de factura
- Fecha de emisión
- Importe total (con IVA)
- Moneda
- Estado

**Mensajes de estado vacío**
- "Sin facturas procesadas en este periodo."
- "No se han encontrado movimientos sin justificante."
- "Este proveedor no tiene facturas archivadas."

**Acciones de confirmación destructiva**
- "¿Desactivar este proveedor? Las facturas históricas se conservarán."
- "Aprobar el lote archivará {n} facturas. Esta acción no se puede deshacer."

**Errores**
- "No se puede archivar: falta el número de factura."
- "Importe no válido. Debe ser un número mayor que cero."
- "Ya existe un archivo con este nombre. La factura queda pendiente de revisión."

**Revisión manual (motivos)**
- Breves y técnicos: "Proveedor no encontrado en el catálogo."
- "Total no identificado o igual a cero."
- "Número de factura ausente o ambiguo."
- Nunca culpar al usuario: "El documento no pudo procesarse automáticamente." (no "Error del usuario").

**Conciliación**
- "Coincidencia encontrada." (no "¡Pago verificado!")
- "No encontrada en este extracto." (no "Factura impagada")
- "Movimiento sin factura registrada."
- "Extracto parcial: cubre del {fecha} al {fecha}."

**Éxito**
- "Lote completado. {n} facturas archivadas, {m} en revisión."
- "Proveedor guardado."
- "Factura archivada en {ruta}."

---

## Iconografía

Usar **Lucide** (MIT, consistente, línea fina). Tamaño estándar: 20px dentro de pantalla, 24px en navegación, 16px dentro de chips o botones pequeños. Color: heredado del contexto (`color-text-secondary` por defecto).

| Elemento            | Icono sugerido           |
|---------------------|--------------------------|
| Factura             | `file-text`              |
| Proveedor           | `building-2`             |
| Estado procesado    | `check-circle`           |
| Revisión manual     | `alert-circle`           |
| Duplicado           | `copy`                   |
| No es factura       | `x-circle`               |
| Conciliación        | `git-compare`            |
| Lote / procesamiento| `layers`                 |
| Banco / extracto    | `landmark`               |
| Archivar            | `archive`                |
| Correo de origen    | `mail`                   |
| Adjunto / PDF       | `paperclip`              |
| Métricas            | `bar-chart-2`            |
| Alerta              | `triangle-alert`         |

---

## Navegación

**Barra inferior** con 4 pestañas principales:

| Pestaña       | Icono         | Ruta principal              |
|---------------|---------------|-----------------------------|
| Facturas      | `file-text`   | Lista de facturas            |
| Proveedores   | `building-2`  | Catálogo de proveedores      |
| Conciliación  | `git-compare` | Conciliación bancaria        |
| Actividad     | `layers`      | Lotes y registro de actividad|

- Pestaña activa: `color-primary`, label `text-xs` weight 600
- Pestaña inactiva: `color-text-muted`, label `text-xs` weight 400
- Indicador de revisiones pendientes: badge rojo `radius-full` encima del icono de Facturas

---

## Accesibilidad

- Contraste mínimo: 4.5:1 para texto normal, 3:1 para texto grande y elementos gráficos.
- Todos los colores de estado cumplen contraste con su fondo de chip correspondiente.
- Tap target mínimo: 44×44px en cualquier elemento interactivo.
- Campos de formulario siempre con label visible (sin depender únicamente del placeholder).
- Los chips de estado incluyen texto, no solo color.
