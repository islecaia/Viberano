"""Progreso efímero de una sincronización en curso, para que la UI pueda sondear (polling)
mientras `analizar_lote()`/`ejecutar_lote()` siguen ejecutándose de forma síncrona dentro de su
propia petición HTTP (research.md de specs/006-lotes-aprobacion-previa/, §7 de la feature 001).

Se guarda en memoria del proceso, no en la base de datos: es puramente informativo para la
pantalla, se pierde sin problema si el proceso se reinicia. Las rutas `def` (no `async def`) de
FastAPI se ejecutan en threads del pool de Starlette, así que una petición GET de sondeo sí puede
atenderse mientras el POST de sincronización sigue en marcha en otro thread; `threading.Lock`
evita una condición de carrera al leer/escribir el mismo mensaje desde threads distintos.
"""

import threading

_lock = threading.Lock()
_mensajes: dict[int, str] = {}


def set_mensaje(cuenta_id: int, mensaje: str) -> None:
    with _lock:
        _mensajes[cuenta_id] = mensaje


def get_mensaje(cuenta_id: int) -> str | None:
    with _lock:
        return _mensajes.get(cuenta_id)


def clear(cuenta_id: int) -> None:
    with _lock:
        _mensajes.pop(cuenta_id, None)
