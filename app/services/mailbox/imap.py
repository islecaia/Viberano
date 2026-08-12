"""ImapConnector: implementa MailboxConnector sobre un buzón IMAP genérico (research.md §1)."""

import email
import hashlib
import imaplib
from datetime import datetime, timedelta
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime

from app.services.mailbox.base import (
    EmailAttachment,
    EmailMessage,
    MailboxConnectionError,
    MailboxConnector,
)

_IMPORT_WINDOW_DAYS = 90
_SUPPORTED_FORMATS = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
}


def _decode(value: str) -> str:
    parts = decode_header(value)
    return "".join(
        part.decode(enc or "utf-8") if isinstance(part, bytes) else part for part, enc in parts
    )


def _clean_error_message(exc: Exception) -> str:
    """imaplib suele lanzar errores con argumentos en bytes (p. ej. b'authentication failed');
    esto los decodifica para que el mensaje mostrado al usuario sea texto legible."""
    parts = [
        arg.decode("utf-8", errors="replace") if isinstance(arg, bytes) else str(arg)
        for arg in exc.args
    ]
    return " ".join(parts) if parts else str(exc)


class ImapConnector(MailboxConnector):
    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password

    def _open(self) -> imaplib.IMAP4_SSL:
        try:
            conn = imaplib.IMAP4_SSL(self._host, self._port)
            conn.login(self._username, self._password)
            return conn
        except (OSError, imaplib.IMAP4.error) as exc:
            raise MailboxConnectionError(_clean_error_message(exc)) from exc

    def connect(self) -> None:
        conn = self._open()
        conn.logout()

    def list_new_messages(self, since: datetime | None) -> list[EmailMessage]:
        tz = since.tzinfo if since else None
        cutoff = since or (datetime.now(tz) - timedelta(days=_IMPORT_WINDOW_DAYS))
        conn = self._open()
        try:
            conn.select("INBOX", readonly=True)
            criterion = f'(SINCE "{cutoff.strftime("%d-%b-%Y")}")'
            status, data = conn.search(None, criterion)
            if status != "OK":
                raise MailboxConnectionError(f"Búsqueda IMAP fallida: {status}")
            messages = []
            for num in data[0].split():
                status, msg_data = conn.fetch(num, "(RFC822)")
                if status != "OK":
                    continue
                raw = msg_data[0][1]
                parsed = email.message_from_bytes(raw)
                messages.append(self._to_email_message(parsed, raw))
            return messages
        finally:
            conn.logout()

    def _to_email_message(self, parsed: Message, raw: bytes) -> EmailMessage:
        message_id = parsed.get("Message-ID", "").strip()
        if not message_id:
            # Revisión de código: sin cabecera Message-ID (correos mal formados o reenviados),
            # todos colisionarían en find_existing() con "" como si fueran el mismo correo,
            # descartando en silencio cualquier correo distinto que llegue después del primero.
            # Se deriva un identificador estable a partir del contenido crudo del mensaje: el
            # mismo correo reprocesado produce el mismo id (dedup real sigue funcionando), pero
            # dos correos distintos ya no colisionan.
            message_id = f"sha256:{hashlib.sha256(raw).hexdigest()}"
        remitente = _decode(parsed.get("From", ""))
        asunto = _decode(parsed.get("Subject", ""))
        fecha = parsedate_to_datetime(parsed.get("Date")) if parsed.get("Date") else datetime.now()

        attachments = []
        for part in parsed.walk():
            content_type = part.get_content_type()
            if content_type not in _SUPPORTED_FORMATS:
                continue
            if part.get_content_disposition() != "attachment":
                continue
            filename = part.get_filename() or "adjunto"
            content = part.get_payload(decode=True) or b""
            attachments.append(
                EmailAttachment(
                    attachment_id=filename,
                    filename=filename,
                    content_type=content_type,
                    content=content,
                )
            )

        return EmailMessage(
            message_id=message_id,
            remitente=remitente,
            asunto=asunto,
            fecha=fecha,
            attachments=attachments,
        )

    def get_attachment(self, message_id: str, attachment_id: str) -> EmailAttachment:
        # En IMAP, list_new_messages ya trae los adjuntos completos; este método existe para
        # cumplir la interfaz cuando el llamador solo conserva el message_id.
        for msg in self.list_new_messages(since=None):
            if msg.message_id != message_id:
                continue
            for attachment in msg.attachments:
                if attachment.attachment_id == attachment_id:
                    return attachment
        raise MailboxConnectionError(f"Adjunto {attachment_id} no encontrado en {message_id}")
