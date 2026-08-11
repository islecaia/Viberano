"""Copia inmutable de adjuntos (research.md §3, Principios III y IV de la constitution).

El nombre de archivo se deriva de (cuenta_id, message_id, attachment_id) — nunca del nombre
original — para que un reintento de sincronización sobre el mismo mensaje nunca produzca una
escritura sobre un archivo ya existente: si el destino ya existe, se reutiliza la referencia en
vez de reescribirlo.
"""

import hashlib
import os
from pathlib import Path


def _store_dir() -> Path:
    path = Path(os.environ.get("ATTACHMENT_STORE_DIR", "./data/attachments"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _derive_key(cuenta_id: int, message_id: str, attachment_id: str) -> str:
    raw = f"{cuenta_id}:{message_id}:{attachment_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def save_attachment(
    cuenta_id: int, message_id: str, attachment_id: str, content: bytes, formato: str
) -> str:
    """Guarda el adjunto si no existe ya; devuelve la ruta de solo lectura (str) al archivo."""
    key = _derive_key(cuenta_id, message_id, attachment_id)
    dest = _store_dir() / f"{key}.{formato}"
    if not dest.exists():
        dest.write_bytes(content)
        dest.chmod(0o444)
    return str(dest)


def read_attachment(archivo_ref: str) -> bytes:
    return Path(archivo_ref).read_bytes()
