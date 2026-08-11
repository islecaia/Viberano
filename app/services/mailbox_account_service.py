"""Conectar una cuenta de correo, comprobar validez de credenciales y actualizar su estado.

Cubre User Story 1 (T016): FR-002 (soporte de Gmail/IMAP/Graph) y FR-003 (estado visible).
"""

from app.models import mailbox_account as mailbox_account_model
from app.services import secret_store
from app.services.mailbox.base import MailboxConnectionError, MailboxConnector
from app.services.mailbox.gmail import GmailConnector
from app.services.mailbox.graph import GraphConnector
from app.services.mailbox.imap import ImapConnector

PROVEEDORES_VALIDOS = {"gmail", "imap", "microsoft_graph"}


class CredencialesInvalidasError(Exception):
    pass


class CuentaYaConectadaError(Exception):
    pass


def build_connector(proveedor: str, credenciales: dict) -> MailboxConnector:
    if proveedor == "imap":
        return ImapConnector(
            host=credenciales["host"],
            port=int(credenciales.get("port", 993)),
            username=credenciales["username"],
            password=credenciales["password"],
        )
    if proveedor == "gmail":
        return GmailConnector(
            access_token=credenciales["access_token"],
            refresh_token=credenciales["refresh_token"],
            client_id=credenciales["client_id"],
            client_secret=credenciales["client_secret"],
        )
    if proveedor == "microsoft_graph":
        return GraphConnector(access_token=credenciales["access_token"])
    raise ValueError(f"Proveedor no soportado: {proveedor}")


def connect_account(
    persona_autorizada: str, proveedor: str, email_address: str, credenciales: dict
) -> mailbox_account_model.MailboxAccount:
    if proveedor not in PROVEEDORES_VALIDOS:
        raise ValueError(f"Proveedor no soportado: {proveedor}")

    if mailbox_account_model.get_for_persona(persona_autorizada) is not None:
        raise CuentaYaConectadaError(
            f"{persona_autorizada} ya tiene una cuenta de correo conectada"
        )

    connector = build_connector(proveedor, credenciales)
    try:
        connector.connect()
    except MailboxConnectionError as exc:
        raise CredencialesInvalidasError(str(exc)) from exc

    credenciales_ref = secret_store.store(credenciales)
    return mailbox_account_model.create(
        persona_autorizada=persona_autorizada,
        proveedor=proveedor,
        email_address=email_address,
        credenciales_ref=credenciales_ref,
    )


def refresh_status(account: mailbox_account_model.MailboxAccount) -> str:
    """Vuelve a comprobar las credenciales guardadas y actualiza `estado` si ha cambiado."""
    credenciales = secret_store.retrieve(account.credenciales_ref)
    connector = build_connector(account.proveedor, credenciales)
    try:
        connector.connect()
    except MailboxConnectionError:
        mailbox_account_model.update_estado(account.id, "requiere_reautorizacion")
        return "requiere_reautorizacion"
    if account.estado != "conectada":
        mailbox_account_model.update_estado(account.id, "conectada")
    return "conectada"
