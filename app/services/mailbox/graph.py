"""GraphConnector: implementa MailboxConnector sobre Microsoft Graph vía OAuth2 (research.md §1).

El SDK de Microsoft Graph es asíncrono; esta clase expone la misma interfaz síncrona que el
resto de conectores envolviendo cada llamada con asyncio.run().
"""

import asyncio
import base64
from datetime import UTC, datetime, timedelta

from azure.core.credentials import AccessToken, TokenCredential
from msgraph import GraphServiceClient

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


class _StaticTokenCredential(TokenCredential):
    """Credential mínima que envuelve un access token ya obtenido (flujo OAuth2 delegado)."""

    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    def get_token(self, *scopes: str, **kwargs) -> AccessToken:
        expires_on = int((datetime.now(UTC) + timedelta(hours=1)).timestamp())
        return AccessToken(self._access_token, expires_on)


class GraphConnector(MailboxConnector):
    def __init__(self, access_token: str) -> None:
        credential = _StaticTokenCredential(access_token)
        self._client = GraphServiceClient(
            credentials=credential, scopes=["Mail.Read"]
        )

    def connect(self) -> None:
        try:
            asyncio.run(self._client.me.get())
        except Exception as exc:  # noqa: BLE001 - la excepción concreta la define el SDK
            raise MailboxConnectionError(str(exc)) from exc

    def list_new_messages(self, since: datetime | None) -> list[EmailMessage]:
        cutoff = since or (datetime.now(UTC) - timedelta(days=_IMPORT_WINDOW_DAYS))
        try:
            return asyncio.run(self._list_new_messages_async(cutoff))
        except MailboxConnectionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise MailboxConnectionError(str(exc)) from exc

    async def _list_new_messages_async(self, cutoff: datetime) -> list[EmailMessage]:
        from msgraph.generated.users.item.messages.messages_request_builder import (
            MessagesRequestBuilder,
        )

        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            filter=f"receivedDateTime ge {cutoff.isoformat()} and hasAttachments eq true",
            expand=["attachments"],
        )
        request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )
        result = await self._client.me.messages.get(request_configuration=request_config)

        messages = []
        for msg in result.value or []:
            attachments = []
            for att in msg.attachments or []:
                content_type = getattr(att, "content_type", "") or ""
                if content_type not in _SUPPORTED_FORMATS:
                    continue
                content_bytes = getattr(att, "content_bytes", None)
                content = base64.b64decode(content_bytes) if content_bytes else b""
                attachments.append(
                    EmailAttachment(
                        attachment_id=att.id,
                        filename=att.name or "adjunto",
                        content_type=content_type,
                        content=content,
                    )
                )
            messages.append(
                EmailMessage(
                    message_id=msg.internet_message_id or msg.id,
                    remitente=(
                        msg.from_
                        and msg.from_.email_address
                        and msg.from_.email_address.address
                    )
                    or "",
                    asunto=msg.subject or "",
                    fecha=msg.received_date_time or datetime.now(UTC),
                    attachments=attachments,
                )
            )
        return messages

    def get_attachment(self, message_id: str, attachment_id: str) -> EmailAttachment:
        # Graph devuelve los adjuntos ya expandidos en list_new_messages; se reutiliza esa vía.
        for msg in self.list_new_messages(since=None):
            if msg.message_id != message_id:
                continue
            for attachment in msg.attachments:
                if attachment.attachment_id == attachment_id:
                    return attachment
        raise MailboxConnectionError(f"Adjunto {attachment_id} no encontrado en {message_id}")
