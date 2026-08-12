# Feature Specification: Lotes con Aprobación Previa y Reanudación

**Feature Branch**: `006-lotes-aprobacion-previa`

**Created**: 2026-08-12

**Status**: Draft

**Input**: User description: "Lotes con aprobación previa y reanudación sin repetir: al iniciar una sincronización, antes de clasificar y guardar ningún documento candidato nuevo, la persona autorizada debe ver un resumen del lote que se va a procesar (cuántos correos nuevos hay desde la última sincronización, cuántos de ellos tienen adjuntos candidatos) y aprobarlo explícitamente antes de que el sistema ejecute la clasificación y el guardado real de esos documentos. Cada lote ejecutado registra su alcance, inicio, fin, cantidad de correos procesados, candidatos generados y errores, igual que ya ocurre hoy con las sincronizaciones. Si la sincronización se interrumpe después de completar el análisis de algunos correos, al reanudar el proceso continúa desde el último punto completado sin volver a procesar correos ya guardados. Si un lote aprobado tiene errores parciales durante su ejecución, los correos procesados correctamente conservan su resultado y los que fallaron quedan identificados para reintentar o revisar, sin que un fallo puntual bloquee el resto del lote."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aprobar un lote antes de procesarlo (Priority: P1) 🎯 MVP

Como persona autorizada, quiero ver cuántos correos nuevos hay y cuántos de ellos podrían contener
facturas antes de que el sistema los procese, para decidir yo misma cuándo lanzar un procesamiento
que puede generar muchos documentos candidatos de golpe.

**Why this priority**: Es el propósito central de la feature — sin este resumen y esta aprobación
explícita, no hay ningún cambio observable respecto al comportamiento actual de sincronizar.

**Independent Test**: Puede probarse conectando una cuenta con varios correos nuevos pendientes,
iniciando la sincronización, y comprobando que se muestra el resumen del lote (correos nuevos,
correos con adjuntos candidatos) sin que se haya creado todavía ningún documento candidato; al
aprobar el lote, los documentos candidatos aparecen.

**Acceptance Scenarios**:

1. **Given** una cuenta conectada con correos nuevos desde la última sincronización, **When** la
   persona autorizada inicia una sincronización, **Then** ve un resumen con el número de correos
   nuevos y cuántos de ellos tienen al menos un adjunto candidato (PDF/JPG/PNG), sin que se haya
   creado ningún documento candidato todavía.
2. **Given** un lote ya analizado y pendiente de aprobación, **When** la persona autorizada lo
   aprueba, **Then** el sistema clasifica y guarda los documentos candidatos correspondientes.
3. **Given** un lote ya analizado y pendiente de aprobación para una cuenta, **When** se intenta
   iniciar el análisis de otro lote para esa misma cuenta, **Then** el sistema lo impide hasta que
   el lote pendiente se apruebe.
4. **Given** una sincronización sin ningún correo nuevo, **When** la persona autorizada la inicia,
   **Then** el resumen indica 0 correos nuevos, sin nada pendiente de aprobar.

---

### User Story 2 - Reanudar sin repetir trabajo ya hecho (Priority: P2)

Como persona autorizada, quiero que una sincronización interrumpida continúe donde se quedó al
reanudarla, para no perder tiempo ni arriesgarme a duplicados al procesar históricos grandes.

**Why this priority**: Protege el trabajo ya realizado en lotes grandes; depende de que exista ya
el concepto de lote aprobado y en ejecución de la Historia de Usuario 1.

**Independent Test**: Puede probarse interrumpiendo un lote aprobado a mitad de su ejecución y
reanudándolo, comprobando que los correos ya guardados no se vuelven a procesar ni duplican.

**Acceptance Scenarios**:

1. **Given** un lote aprobado cuya ejecución se interrumpió tras guardar algunos correos,
   **When** la persona autorizada reanuda el procesamiento, **Then** continúa desde el último
   correo completado, sin volver a analizar ni guardar los correos ya guardados.
2. **Given** un correo y sus adjuntos ya guardados como documentos candidatos en un lote anterior,
   **When** se reanuda o se repite el análisis de un lote que vuelve a incluir ese correo,
   **Then** no se crea ningún documento candidato duplicado para él.

---

### User Story 3 - Ver y reintentar los correos que fallaron (Priority: P3)

Como persona autorizada, quiero saber qué correos de un lote no se pudieron procesar y por qué,
y poder reintentarlos, para no perder facturas por un fallo puntual sin tener que repetir todo
el lote.

**Why this priority**: Mejora la resiliencia operativa del procesamiento por lotes, pero el valor
principal (aprobar antes de procesar) ya se entrega con la Historia de Usuario 1.

**Independent Test**: Puede probarse simulando que el procesamiento de un correo concreto falla
dentro de un lote con varios correos, comprobando que los demás se guardan igualmente y que el
fallido queda visible con su motivo y disponible para reintentar.

**Acceptance Scenarios**:

1. **Given** un lote aprobado en el que el procesamiento de un correo concreto falla, **When**
   el lote termina, **Then** los correos procesados correctamente conservan su resultado y el
   fallido queda identificado con el motivo del fallo.
2. **Given** un correo fallido dentro de un lote ya ejecutado, **When** la persona autorizada
   pide reintentarlo, **Then** el sistema vuelve a intentar su procesamiento sin repetir los
   correos que ya se guardaron correctamente.

---

### Edge Cases

- ¿Qué ocurre si la persona autorizada cierra la pantalla sin aprobar el lote analizado? → El
  lote queda pendiente de aprobación; puede retomarse más tarde sin volver a analizarlo desde
  cero ni perder el resumen ya calculado.
- ¿Qué ocurre si todos los correos de un lote fallan? → El lote termina con 0 candidatos
  generados y todos los correos identificados como fallidos, disponibles para reintentar.
- ¿Qué ocurre si se reintenta un correo fallido y vuelve a fallar? → Sigue identificado como
  fallido con el motivo más reciente; puede reintentarse de nuevo sin límite de intentos definido
  en esta versión.
- ¿Qué ocurre si la cuenta se desconecta mientras hay un lote pendiente de aprobación o en
  ejecución? → El lote pendiente o en curso queda con su estado tal cual; no se aprueba ni se
  ejecuta automáticamente al reconectar la cuenta.
- ¿Qué ocurre si el análisis no encuentra ningún correo con posible factura adjunta (ni correos
  nuevos en absoluto, ni correos nuevos sin ningún adjunto candidato)? → No se crea ningún
  registro de lote — no hay nada que la persona autorizada necesite aprobar o descartar — y la
  cuenta queda libre de inmediato para una nueva sincronización, sin esperar ninguna acción.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE, al iniciar una sincronización, identificar los correos nuevos
  desde el último punto completado sin crear todavía ningún documento candidato.
- **FR-002**: El sistema DEBE mostrar a la persona autorizada, antes de procesar nada, un resumen
  del lote identificado: número de correos nuevos y cuántos de ellos tienen al menos un adjunto
  candidato (PDF/JPG/PNG).
- **FR-003**: El sistema NO DEBE clasificar ni guardar ningún documento candidato de un lote
  identificado hasta que la persona autorizada lo apruebe explícitamente.
- **FR-004**: El sistema DEBE permitir a la persona autorizada aprobar un lote identificado para
  que se ejecute su procesamiento completo (clasificación y guardado de documentos candidatos).
- **FR-005**: El sistema NO DEBE permitir iniciar el análisis de un nuevo lote para una cuenta
  mientras exista un lote de esa cuenta ya identificado y pendiente de aprobación, o un lote de
  esa cuenta todavía en ejecución.
- **FR-006**: El sistema DEBE registrar, para cada lote, su alcance (cuenta), inicio, fin, número
  de correos procesados, número de candidatos generados y los errores ocurridos.
- **FR-007**: El sistema DEBE permitir reanudar el procesamiento de un lote aprobado tras una
  interrupción, continuando desde el último correo completado, sin volver a analizar ni procesar
  correos ya guardados.
- **FR-008**: El sistema NO DEBE crear un documento candidato duplicado para un correo o adjunto
  ya procesado en un lote anterior, incluso si ese lote se reanuda o se repite su análisis.
- **FR-009**: El sistema DEBE continuar procesando el resto de un lote aprobado aunque el
  procesamiento de un correo concreto de ese lote falle.
- **FR-010**: El sistema DEBE dejar identificado, para cada correo de un lote aprobado que falló
  al procesarse, el motivo del fallo, de forma visible para la persona autorizada.
- **FR-011**: El sistema DEBE permitir a la persona autorizada reintentar el procesamiento de los
  correos que fallaron dentro de un lote ya ejecutado.
- **FR-012**: El sistema DEBE iniciar el análisis, la aprobación y el reintento de cada lote
  únicamente por acción explícita de la persona autorizada, nunca de forma programada o
  automática.
- **FR-013**: El sistema NO DEBE crear ningún registro de lote cuando el análisis no encuentra
  ningún correo con al menos un adjunto candidato; en ese caso la cuenta DEBE quedar libre de
  inmediato para una nueva sincronización, sin ningún lote pendiente que la bloquee.

### Key Entities

- **Lote de Sincronización**: ampliación de la Sincronización ya existente (feature 001). Añade
  un estado "pendiente de aprobación" previo a su ejecución, con el resumen calculado (correos
  nuevos, correos con adjuntos candidatos); conserva alcance, inicio, fin, correos procesados,
  candidatos generados y errores una vez ejecutado. Solo llega a existir como registro cuando el
  resumen tiene al menos un correo con adjunto candidato (FR-013) — un análisis sin nada que
  aprobar no deja rastro.
- **Correo Fallido**: referencia a un correo dentro de un lote cuyo procesamiento no se completó;
  conserva el motivo del fallo y si ya se ha reintentado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los lotes muestra su resumen (correos nuevos, correos con adjuntos
  candidatos) antes de que se cree ningún documento candidato nuevo.
- **SC-002**: El 100% de las reanudaciones tras una interrupción no vuelve a procesar ningún
  correo ya guardado en un intento anterior del mismo lote.
- **SC-003**: Cuando un lote tiene errores parciales, el 100% de los correos procesados
  correctamente conserva su resultado, y el 100% de los fallidos queda identificado con su
  motivo, visible sin consultar directamente la base de datos.
- **SC-004**: La persona autorizada puede aprobar un lote y consultar su resultado completo
  (correos procesados, candidatos generados, errores) desde la propia aplicación.

## Assumptions

- No existe una acción explícita de "rechazar" un lote pendiente de aprobación en esta primera
  versión: la persona simplemente no lo aprueba; el lote queda pendiente hasta que decida
  aprobarlo, coherente con que ninguna acción es programada o automática (Principio V).
- Solo puede existir un lote pendiente de aprobación o en ejecución por cuenta a la vez — mismo
  criterio que ya rige la sincronización de la feature 001 (FR-005).
- El resumen previo a la aprobación identifica los correos con adjuntos candidatos por su tipo de
  archivo (PDF/JPG/PNG); no requiere clasificar ni extraer texto de esos adjuntos, ya que esa es
  precisamente la parte del procesamiento que se difiere hasta la aprobación (Principio VII: la
  IA no se invoca hasta que la persona aprueba el lote).
- Reintentar un correo fallido reutiliza el mismo lote — no crea un lote nuevo — y también
  requiere una acción explícita de la persona autorizada.
- Esta feature no cambia el comportamiento de validación y archivado (feature 002): los
  documentos candidatos generados tras aprobar un lote siguen exigiendo revisión manual antes de
  PROCESADA, igual que hoy.
- No se define un límite de reintentos para un correo fallido en esta primera versión.
