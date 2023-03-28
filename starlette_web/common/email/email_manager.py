from typing import Optional, List, TypedDict, Dict, Type

from starlette_web.common.conf import settings
from starlette_web.common.email.base_sender import BaseEmailSender
from starlette_web.common.http.exceptions import ImproperlyConfigured
from starlette_web.common.utils.importing import import_string


class EmailSenderSettings(TypedDict):
    BACKEND: str
    OPTIONS: Dict


class EmailManager:
    sender: Optional[BaseEmailSender] = None

    def _switch_to_email_sender_class(self, sender_settings: EmailSenderSettings):
        try:
            backend: Type[BaseEmailSender] = import_string(sender_settings["BACKEND"])
            self.sender = backend(**sender_settings["OPTIONS"])
        except (ImportError, SystemError, TypeError):
            raise ImproperlyConfigured(
                "settings.EMAIL_SENDER is not a valid import path to a callable"
            )

        if not isinstance(self.sender, BaseEmailSender):
            raise ImproperlyConfigured(
                "Class, specified with settings.EMAIL_SENDER, "
                "is not a subclass of BaseEmailSender"
            )

    def _get_email_sender(self) -> BaseEmailSender:
        if self.sender:
            return self.sender

        self._switch_to_email_sender_class(settings.EMAIL_SENDER)
        return self.sender

    async def send_email(
        self,
        subject: str,
        html_content: str,
        recipients_list: List[str],
        from_email: Optional[str] = None,
    ):
        async with self._get_email_sender() as sender:
            await sender.send_email(subject, html_content, recipients_list, from_email=from_email)


_email_manager = EmailManager()
send_email = _email_manager.send_email
