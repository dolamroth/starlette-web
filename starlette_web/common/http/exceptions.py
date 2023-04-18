from typing import Optional

import httpx

from starlette_web.common.i18n import gettext as _


class BaseApplicationError(Exception):
    message: str = httpx.codes.INTERNAL_SERVER_ERROR.name
    details: Optional[str] = None
    status_code: int = 500

    def __init__(
        self,
        details: str = None,
        message: str = None,
        status_code: int = None,
    ):
        self.message = message or self.message
        self.details = details or self.details
        self.status_code = status_code or self.status_code

    def __str__(self):
        return f"{self.message}\n{self.details}".strip()

    def __iter__(self):
        yield "message", self.message
        yield "details", self.details
        yield "status_code", self.status_code


class ImproperlyConfigured(BaseApplicationError):
    message = _("Application is configured improperly.")


class UnexpectedError(BaseApplicationError):
    message = _("Something unexpected happened.")


class NotSupportedError(BaseApplicationError):
    message = _("Requested action is not supported now.")


class InvalidParameterError(BaseApplicationError):
    status_code = 400
    message = _("Requested data is not valid.")


class AuthenticationFailedError(BaseApplicationError):
    status_code = 401
    message = _("Authentication credentials are invalid.")


class AuthenticationRequiredError(AuthenticationFailedError):
    message = _("Authentication is required.")


class SignatureExpiredError(AuthenticationFailedError):
    message = _("Authentication credentials have expired.")


class InviteTokenInvalidationError(AuthenticationFailedError):
    message = _("Requested token is expired or does not exist.")


class PermissionDeniedError(BaseApplicationError):
    status_code = 403
    message = _("You do not have permission to perform this action.")


class NotFoundError(BaseApplicationError):
    status_code = 404
    message = _("Requested object not found.")


class MethodNotAllowedError(BaseApplicationError):
    status_code = 405
    message = _("Requested method is not allowed.")


class NotAcceptableError(BaseApplicationError):
    status_code = 406
    message = _(
        "Request cannot be processed, "
        "Accept-* headers are incompatible with server."
    )


class ConflictError(BaseApplicationError):
    status_code = 409
    message = _("Request conflicts with current state of server.")


class UnprocessableEntityError(BaseApplicationError):
    status_code = 422
    message = _("Could not process request due to logical errors in data.")


class InvalidResponseError(BaseApplicationError):
    status_code = 500
    message = _("Response data could not be serialized.")


class NotImplementedByServerError(BaseApplicationError):
    status_code = 501
    message = _("Functionality is not supported by the server.")


class HttpError(BaseApplicationError):
    status_code = 502
    message = _("Some HTTP error happened.")


class SendRequestError(BaseApplicationError):
    status_code = 503
    message = _("Got unexpected error for sending request.")


class MaxAttemptsReached(BaseApplicationError):
    status_code = 503
    message = _("Reached max attempt to make action")
