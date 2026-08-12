# Implementation Plan: Volumen Mensual de Facturas

**Branch**: `005-volumen-mensual-facturas` | **Date**: 2026-08-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-volumen-mensual-facturas/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Consulta de solo lectura que muestra, para un periodo elegido por la persona autorizada, el
número de facturas `PROCESADA` archivadas en cada mes (por `fecha_factura`) y la media del
periodo, distinguiendo la media de meses completos de la que incluye un mes parcial (el mes en
curso, o el primer mes de la cuenta conectada si empezó a mitad de mes). Enfoque técnico: sin
dependencias nuevas ni cambios de esquema — se agrega `candidate_documents` ya existente
(`estado`, `fecha_factura`) agrupando por año-mes; la pestaña **Actividad** de la barra inferior
(hoy placeholder) pasa a alojar esta consulta, reemplazando su propósito original de "historial de
acciones" por decisión explícita del usuario (ver conversación de planificación).

## Technical Context

**Language/Version**: Python 3.11+ (mismo proyecto que las features 001-004)

**Primary Dependencies**: Ninguna dependencia nueva — `datetime`/`calendar` (estándar) para la
aritmética de meses completos/parciales; FastAPI y Jinja2 ya presentes.

**Storage**: SQLite (sin migración nueva). Se lee `candidate_documents.estado` y
`.fecha_factura`, ya existentes desde la feature 001/002, y `mailbox_accounts.fecha_conexion`
(feature 001) para determinar si el primer mes de actividad es parcial. No se persiste ningún
recuento ni media — se calculan en el momento de la consulta (spec.md § Key Entities).

**Testing**: pytest disponible; sin tests dedicados salvo que se solicite explícitamente (mismo
criterio que las features 001-004) — verificación funcional vía script en proceso más los
escenarios de quickstart.md.

**Target Platform**: la misma app web única — no se añade ningún componente desplegable nuevo.

**Project Type**: extensión del proyecto único ya existente (`app/`).

**Performance Goals**: mostrar el volumen mensual de un periodo típico de 12 meses en menos de 5
segundos (SC-004).

**Constraints**: la consulta es de solo lectura — no crea, modifica ni archiva ninguna factura
(FR-009); todo mes del periodo aparece con recuento (0 si no hay facturas), nunca se omite
(FR-005); un mes parcial nunca se mezcla silenciosamente dentro de "meses completos" (FR-008).

**Scale/Scope**: una sola cuenta de correo conectada por persona autorizada (spec.md,
Assumptions) — el único mes potencialmente parcial por inicio de actividad es el de conexión de
esa cuenta; sin desglose por proveedor.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / Sección | Estado | Cómo lo cumple el diseño |
|---|---|---|
| I. No Invención de Datos | PASS | El recuento de cada mes es un conteo directo de facturas `PROCESADA` reales (sin estimar ni interpolar); un mes anterior a cualquier dato existente en el sistema se muestra como 0 porque, literalmente, no hay ninguna factura PROCESADA que pertenezca a él — no se inventa un valor "desconocido" (spec.md, Edge Cases). |
| II. Validación Obligatoria Antes de Archivar | N/A | Esta feature no archiva ni valida nada; solo agrega datos ya validados por la feature 002. |
| III. Inmutabilidad de Originales | N/A | No toca correos, adjuntos ni ningún dato de origen. |
| IV. No Sobrescritura de Archivos | N/A | No crea ni sobrescribe ningún archivo — es una consulta agregada, sin persistencia nueva. |
| V. Control Humano Explícito | PASS | La consulta solo se ejecuta cuando la persona abre la pestaña Actividad o cambia el periodo; no hay ningún cálculo programado ni recurrente. |
| VI. Precisión en Estados de Conciliación | N/A | Esta feature no toca `estado_conciliacion` ni la conciliación bancaria. |
| VII. Uso Acotado de IA de Pago | PASS (N/A ampliado) | No usa la Anthropic API ni ningún modelo — es agregación aritmética determinista sobre datos ya existentes. |
| Autenticación y Control de Acceso | PASS | El endpoint nuevo queda bajo el mismo `api_router` protegido por sesión de persona autorizada. |
| Sistema de Diseño | PASS (aplica a la UI) | La pantalla de Actividad debe seguir Montserrat, `#0062FF`, tarjetas de 12px, igual que el resto de pantallas (base.html). |

No hay violaciones que requieran justificación en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/005-volumen-mensual-facturas/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── models/
│   └── candidate_document.py        # + count_procesada_por_mes(fecha_inicio, fecha_fin)
├── services/
│   └── metrics_service.py           # nuevo: calcula meses completos/parciales y ambas medias
├── api/routes/
│   └── metrics.py                   # nuevo: GET /api/metrics/volumen-mensual
├── web.py                           # actividad_page() pasa a consultar metrics_service
└── templates/
    └── activity.html                # nuevo: sustituye placeholder.html en /actividad

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: se extiende el mismo proyecto único de las features 001-004 (`app/`); no
se crea ningún componente nuevo desplegable. La pestaña Actividad deja de usar
`app/templates/placeholder.html` (que sigue existiendo para futuras pantallas placeholder que no
sean esta) y pasa a usar `app/templates/activity.html`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No aplica: el Constitution Check no registra ninguna violación (todas las filas son PASS o N/A).
