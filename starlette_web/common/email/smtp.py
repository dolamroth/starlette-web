from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Sequence

import aiosmtplib
import anyio

from starlette_web.common.email.base_sender import BaseEmailSender
from starlette_web.common.http.exceptions import NotSupportedError
from starlette_web.common.utils import safe_init


class SMTPEmailSender(BaseEmailSender):
    SEND_MAX_TIME = 30
    _client: Optional[aiosmtplib.SMTP] = None

    async def _open(self):
        self._client = safe_init(aiosmtplib.SMTP, **self.options)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.__aexit__(exc_type, exc_val, exc_tb)

    async def send_email(
        self,
        subject: str,
        html_content: str,
        recipients_list: Sequence[str],
        from_email: Optional[str] = None,
        attachments: Optional[Sequence[MIMEBase]] = None,
        **kwargs,
    ):
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        _from = from_email
        if _from is None:
            _from = self.options.get("from")
        if _from is None:
            raise NotSupportedError(details="Cannot send email without setting FROM field.")
        message["From"] = _from

        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        if attachments:
            for attachment in attachments:
                message.attach(attachment)

        _recipients = list(recipients_list).copy()

        while _recipients:
            with anyio.move_on_after(self.SEND_MAX_TIME):
                await self._client.send_message(
                    message,
                    sender=str(_from),
                    recipients=recipients_list,
                    mail_options=kwargs.get("mail_options"),
                    rcpt_options=kwargs.get("rcpt_options"),
                    timeout=kwargs.get("timeout", aiosmtplib.typing._default),
                )
            del _recipients[: self.MAX_BULK_SIZE]
