# Research: Conciliación Bancaria

**Fase**: 0 — Outline & Research
**Fecha**: 2026-08-11
**Spec**: [spec.md](./spec.md)

Esta feature extiende la app ya construida en `specs/001-.../002-.../003-.../`. No se introduce
ningún stack nuevo.

## 1. Cómo se aporta el extracto: subida de archivo, periodo inferido

- **Decision**: `POST /api/reconciliations` acepta un archivo CSV (`multipart/form-data`, usando
  `python-multipart`, ya dependencia de la feature 001). El periodo cubierto (`fecha_inicio`,
  `fecha_fin`) se infiere directamente del mínimo y máximo de la columna `fecha` de los
  movimientos parseados — no se pide como campo aparte.
- **Rationale**: Reduce la información que la persona autorizada tiene que introducir a mano; el
  propio extracto ya contiene esa información. No requiere ninguna librería nueva.
- **Alternatives considered**: Pedir `fecha_inicio`/`fecha_fin` explícitos en el formulario →
  descartado por redundante; si no coinciden con el contenido real del CSV, sería una fuente de
  error de usuario innecesaria.

## 2. Formato y validación del CSV (FR-011)

- **Decision**: Se exigen exactamente tres columnas por cabecera (`fecha`, `importe`, `concepto`,
  comparación insensible a mayúsculas). El parseo usa el módulo estándar `csv` de Python — no se
  añade ninguna dependencia nueva. Si falta alguna columna, si el archivo no es CSV válido, o si
  alguna fila no tiene `fecha`/`importe` parseables, se rechaza el aporte completo (no se crea
  ningún `BankStatement` ni `BankMovement` parcial) con un mensaje que indica el motivo.
- **Rationale**: Cumple FR-011 (rechazar sin marcar nada) de forma simple y sin dependencias
  nuevas; todo-o-nada evita dejar un extracto a medio importar.
- **Alternatives considered**: Aceptar filas válidas e ignorar las inválidas → descartado; un
  extracto parcialmente importado sin que la persona lo sepa iría en contra de la trazabilidad
  que exige el dominio (facturación/contabilidad).

## 3. Algoritmo de "coincidencia inequívoca" (FR-002, FR-003, FR-005)

- **Decision**: Para cada factura `PROCESADA` dentro del periodo del extracto:
  1. Se buscan movimientos candidatos: `abs(movimiento.importe) == factura.total` Y
     `movimiento.fecha` dentro de una ventana de ±10 días de `factura.fecha_factura` Y el
     movimiento no está ya vinculado a otra factura (FR-009).
  2. Si hay **exactamente un** candidato → se concilia automáticamente (FR-003): importe exacto +
     fecha próxima + ser el único candidato ya es una coincidencia inequívoca, tenga o no el
     nombre del proveedor en el concepto (la presencia del nombre del proveedor en el concepto
     solo se usa como señal adicional para el `motivo` mostrado, no como condición obligatoria).
  3. Si hay **cero** candidatos → "no encontrada en el extracto" (FR-004).
  4. Si hay **más de un** candidato → pendiente de revisión manual (FR-005), con todos los
     candidatos guardados para que la persona elija.
- **Rationale**: Es un criterio determinista, explicable y verificable (SC-004: ≥90% de
  coincidencias inequívocas detectadas sin intervención), sin necesitar IA ni heurísticas
  difusas — coherente con el Principio I (no inventar una coincidencia sin evidencia clara) y con
  el Principio VII (esta feature no usa ningún modelo de pago).
- **Alternatives considered**: Puntuación ponderada (score) combinando importe/fecha/texto con un
  umbral → descartado por menos explicable y más difícil de justificar ante una persona que
  audite el resultado; el criterio "único candidato exacto en importe+ventana de fecha" ya cubre
  el caso común sin necesitar afinar pesos.

## 4. Evitar duplicados entre conciliaciones sin persistir un identificador bancario (FR-009)

- **Decision**: No se implementa deduplicación de movimientos en bruto entre distintos extractos
  aportados (cada aporte crea su propio lote de `BankMovement`). La garantía de FR-009 se apoya
  en que **una factura ya conciliada o marcada "no encontrada" es un estado estable** (Assumption
  de spec.md): al volver a aportar un extracto solapado, las facturas ya resueltas no se
  reevalúan, así que no pueden generar un vínculo duplicado.
- **Rationale**: Deduplicar movimientos en bruto por `(fecha, importe, concepto)` sin un
  identificador de transacción del banco es inherentemente frágil (dos cargos idénticos el mismo
  día son indistinguibles de una fila duplicada). Como el mecanismo real de "no duplicar" ya lo
  garantiza la estabilidad del estado de la factura, añadir una heurística de deduplicación de
  movimientos no aporta nada y sí introduce riesgo de ocultar movimientos legítimos.
- **Alternatives considered**: Deduplicar por `(fecha, importe, concepto)` exactos → descartado
  por lo anterior. Conocido trade-off documentado: si se reaporta un extracto solapado, los
  movimientos de cargo ya vinculados no vuelven a aparecer como "pendientes de justificar" (siguen
  vinculados), pero un movimiento de cargo que nunca se vinculó sí podría listarse dos veces si el
  extracto se aporta dos veces — aceptable para esta primera versión (User Story 3 es solo
  informativa, no ejecuta ninguna acción sobre esos movimientos).

## 5. Ingresos y traspasos internos (FR-008)

- **Decision**: Un movimiento con `importe > 0` (ingreso) nunca aparece en "pendientes de
  justificar". Detectar automáticamente un "traspaso entre cuentas propias" no es posible de
  forma fiable con un único extracto de una sola cuenta (research.md de spec.md ya asume una sola
  cuenta) — se deja a criterio visual de la persona autorizada al revisar la lista, coherente con
  el Principio V (la decisión final la toma un humano).
- **Rationale**: Distinguir un traspaso interno de un cargo real requeriría cruzar con el extracto
  de la otra cuenta implicada, fuera del alcance de esta feature (una sola cuenta, spec.md
  Assumptions).
- **Alternatives considered**: Heurística por texto en `concepto` (p. ej. contiene "traspaso") →
  descartada por poco fiable entre distintos bancos y formatos de concepto; se prefiere no
  inventar una regla frágil.

## 6. Modelo de datos: ampliar `candidate_documents` en vez de una tabla de vínculo genérica

- **Decision**: La conciliación de una factura se guarda como dos columnas nuevas en
  `candidate_documents` (`estado_conciliacion`, `movimiento_bancario_id`), más una tabla nueva
  `reconciliation_candidates` que solo se usa mientras una factura está pendiente de revisión
  manual (FR-005/FR-006), para guardar la lista de movimientos candidatos entre los que la
  persona elige.
- **Rationale**: Mismo patrón ya usado en la feature 002 (ampliar `candidate_documents` en vez de
  una tabla 1:1 aparte) — la relación factura↔conciliación es 1:1 salvo en el caso ambiguo
  temporal, que sí necesita una relación 1:N transitoria.
- **Alternatives considered**: Tabla `reconciliations` separada 1:1 con `candidate_documents` →
  descartada por la misma razón que en la feature 002 (research.md §3 de esa feature): añadiría
  un `JOIN` a cada lectura sin aportar nada, dado que ninguna factura tiene más de una
  conciliación activa a la vez.

## Resumen de resolución de Assumptions de spec.md

| Assumption en spec.md | Traducción técnica |
|---|---|
| Extracto en CSV con fecha/importe/concepto | Validación estricta de cabecera (research.md §2), sin librerías nuevas. |
| Criterio de "coincidencia inequívoca" | Importe exacto + ventana de ±10 días + único candidato (research.md §3). |
| Estado estable, sin reevaluación automática | Es también el mecanismo que evita duplicados entre conciliaciones (research.md §4). |
| Una sola cuenta/divisa | Ningún campo de cuenta bancaria en el modelo; se asume implícitamente. |

No quedan `NEEDS CLARIFICATION` pendientes en el Technical Context de plan.md.
