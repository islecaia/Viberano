"""GmailConnector: implementa MailboxConnector sobre la Gmail API vía OAuth2 (research.md §1)."""

import base64
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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


class GmailConnector(MailboxConnector):
    def __init__(
        self, access_token: str, refresh_token: str, client_id: str, client_secret: str
    ) -> None:
        self._credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )

    def _service(self):
        try:
            return build("gmail", "v1", credentials=self._credentials, cache_discovery=False)
        except HttpError as exc:
            raise MailboxConnectionError(str(exc)) from exc

    def connect(self) -> None:
        try:
            self._service().users().getProfile(userId="me").execute()
        except HttpError as exc:
            raise MailboxConnectionError(str(exc)) from exc

    def list_new_messages(self, since: datetime | None) -> list[EmailMessage]:
        cutoff = since or (datetime.now() - timedelta(days=_IMPORT_WINDOW_DAYS))
        query = f"after:{int(cutoff.timestamp())} has:attachment"
        service = self._service()
        try:
            result = service.users().messages().list(userId="me", q=query).execute()
        except HttpError as exc:
            raise MailboxConnectionError(str(exc)) from exc

        messages = []
        for item in result.get("messages", []):
            full = (
                service.users()
                .messages()
                .get(userId="me", id=item["id"], format="full")
                .execute()
            )
            messages.append(self._to_email_message(service, full))
        return messages

    def _to_email_message(self, service, full: dict) -> EmailMessage:
        headers = {h["name"]: h["value"] for h in full["payload"].get("headers", [])}
        message_id = headers.get("Message-ID", full["id"])
        remitente = headers.get("From", "")
        asunto = headers.get("Subject", "")
        fecha = datetime.fromtimestamp(int(full["internalDate"]) / 1000)

        attachments = []
        for part in full["payload"].get("parts", []) or []:
            content_type = part.get("mimeType", "")
            filename = part.get("filename", "")
            body = part.get("body", {})
            if content_type not in _SUPPORTED_FORMATS or not filename or "attachmentId" not in body:
                continue
            attachments.append(
                EmailAttachment(
                    attachment_id=body["attachmentId"],
                    filename=filename,
                    content_type=content_type,
                    content=b"",  # se descarga bajo demanda vía get_attachment
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
        service = self._service()
        try:
            data = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )
        except HttpError as exc:
            raise MailboxConnectionError(str(exc)) from exc
        content = base64.urlsafe_b64decode(data["data"])
        return EmailAttachment(
            attachment_id=attachment_id, filename="", content_type="", content=content
        )
