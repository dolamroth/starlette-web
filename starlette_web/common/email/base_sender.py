from typing import Optional, Sequence

import anyio

from starlette_web.common.http.exceptions import BaseApplicationError


class EmailSenderError(BaseApplicationError):
    status_code = 503
    message = "Error when sending email."


class BaseEmailSender:
    MAX_BULK_SIZE = 1
    EXIT_MAX_DELAY = 60

    def __init__(self, **options):
        self._connection_opened = False
        self.options = options

    async def _open(self):
        return self

    async def _close(self):
        pass

    async def __aenter__(self):
        try:
            if not self._connection_opened:
                await self._open()
                self._connection_opened = True
            return self

        except Exception as exc:
            with anyio.fail_after(self.EXIT_MAX_DELAY, shield=True):
                if self._connection_opened:
                    await self._close()
                    self._connection_opened = False

            raise EmailSenderError(details=str(exc)) from exc

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        with anyio.fail_after(self.EXIT_MAX_DELAY, shield=True):
            if self._connection_opened:
                await self._close()
                self._connection_opened = False

        if exc_type:
            raise EmailSenderError(details=str(exc_val)) from exc_val

    async def send_email(
        self,
        subject: str,
        html_content: str,
        recipients_list: Sequence[str],
        from_email: Optional[str] = None,
    ):
        raise NotImplementedError
