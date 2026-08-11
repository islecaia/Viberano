"""Almacén opaco de credenciales de buzón (data-model.md: `credenciales_ref`).

Las credenciales nunca se guardan en texto plano en la tabla mailbox_accounts; se guardan aquí,
en un archivo separado con permisos restringidos, y la tabla solo referencia su identificador.
No es un KMS — es la implementación mínima suficiente para esta feature (research.md §6).
"""

import json
import os
import uuid
from pathlib import Path


def _store_dir() -> Path:
    path = Path(os.environ.get("ATTACHMENT_STORE_DIR", "./data/attachments")).parent / "secrets"
    path.mkdir(parents=True, exist_ok=True)
    return path


def store(credenciales: dict) -> str:
    ref = str(uuid.uuid4())
    dest = _store_dir() / f"{ref}.json"
    dest.write_text(json.dumps(credenciales), encoding="utf-8")
    dest.chmod(0o600)
    return ref


def retrieve(ref: str) -> dict:
    dest = _store_dir() / f"{ref}.json"
    return json.loads(dest.read_text(encoding="utf-8"))
