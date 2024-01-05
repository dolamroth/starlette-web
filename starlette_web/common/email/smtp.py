from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Sequence

import aiosmtplib
import anyio

from starlette_web.common.email.base_sender import BaseEmailSender
from starlette_web.common.http.exceptions import NotSupportedError
from starlette_web.common.utils import get_available_options


class SMTPEmailSender(BaseEmailSender):
    SEND_MAX_TIME = 30

    async def send_email(
        self,
        subject: str,
        html_content: str,
        recipients_list: Sequence[str],
        from_email: Optional[str] = None,
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

        _recipients = list(recipients_list).copy()
        while _recipients:
            available_args = get_available_options(aiosmtplib.send)
            options = dict(
                sender=_from,
                recipients=_recipients[: self.MAX_BULK_SIZE],
                **self.options,
            )

            with anyio.move_on_after(self.SEND_MAX_TIME):
                await aiosmtplib.send(
                    message,
                    **{key: value for key, value in options.items() if key in available_args}
                )

            del _recipients[: self.MAX_BULK_SIZE]
