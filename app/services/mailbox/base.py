"""Interfaz común MailboxConnector (research.md §1).

El resto del sistema (detección, clasificación, listado) solo conoce esta interfaz, nunca los
detalles de Gmail/IMAP/Microsoft Graph. Ningún método de esta interfaz permite modificar, mover
o eliminar un mensaje o adjunto original (Principio III de la constitution) — todos son de
solo lectura.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EmailAttachment:
    attachment_id: str
    filename: str
    content_type: str
    content: bytes


@dataclass(frozen=True)
class EmailMessage:
    message_id: str
    remitente: str
    asunto: str
    fecha: datetime
    attachments: list[EmailAttachment]


class MailboxConnectionError(Exception):
    """Fallo de autenticación/conexión con el proveedor de correo (research.md §5, §6)."""


class MailboxConnector(ABC):
    """Contrato común para Gmail, IMAP y Microsoft Graph."""

    @abstractmethod
    def connect(self) -> None:
        """Verifica que las credenciales son válidas. Lanza MailboxConnectionError si no."""

    @abstractmethod
    def list_new_messages(self, since: datetime | None) -> list[EmailMessage]:
        """Lista mensajes recibidos desde `since` (o desde la ventana de 90 días si es None).

        Solo lectura: no marca como leído, no mueve ni elimina nada en el buzón de origen.
        """

    @abstractmethod
    def get_attachment(self, message_id: str, attachment_id: str) -> EmailAttachment:
        """Descarga un adjunto concreto de un mensaje ya listado."""
