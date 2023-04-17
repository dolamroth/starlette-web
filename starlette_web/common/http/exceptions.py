from typing import Optional

import httpx


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
    message = httpx.codes.INTERNAL_SERVER_ERROR.name


class UnexpectedError(BaseApplicationError):
    message = httpx.codes.INTERNAL_SERVER_ERROR.name


class NotSupportedError(BaseApplicationError):
    message = httpx.codes.NOT_IMPLEMENTED.name


class InvalidParameterError(BaseApplicationError):
    status_code = 400
    message = httpx.codes.BAD_REQUEST.name


class AuthenticationFailedError(BaseApplicationError):
    status_code = 401
    message = httpx.codes.UNAUTHORIZED.name


class AuthenticationRequiredError(AuthenticationFailedError):
    details = "Authentication is required."


class SignatureExpiredError(AuthenticationFailedError):
    details = "Authentication credentials are invalid."


class InviteTokenInvalidationError(AuthenticationFailedError):
    details = "Requested token is expired or does not exist."


class PermissionDeniedError(BaseApplicationError):
    status_code = 403
    message = httpx.codes.FORBIDDEN.name


class NotFoundError(BaseApplicationError):
    status_code = 404
    message = httpx.codes.NOT_FOUND.name


class MethodNotAllowedError(BaseApplicationError):
    status_code = 405
    message = httpx.codes.METHOD_NOT_ALLOWED.name


class NotAcceptableError(BaseApplicationError):
    status_code = 406
    message = httpx.codes.NOT_ACCEPTABLE.name
    details = (
        "Request cannot be processed, "
        "Accept-* headers are incompatible with server."
    )


class ConflictError(BaseApplicationError):
    status_code = 409
    message = httpx.codes.CONFLICT.name


class UnprocessableEntityError(BaseApplicationError):
    status_code = 422
    message = httpx.codes.UNPROCESSABLE_ENTITY.name


class InvalidResponseError(BaseApplicationError):
    status_code = 500
    message = httpx.codes.INTERNAL_SERVER_ERROR.name
    details = "Response data could not be serialized."


class NotImplementedByServerError(BaseApplicationError):
    status_code = 501
    message = httpx.codes.NOT_IMPLEMENTED.name


class HttpError(BaseApplicationError):
    status_code = 502
    message = httpx.codes.BAD_GATEWAY.name


class SendRequestError(BaseApplicationError):
    status_code = 503
    message = httpx.codes.SERVICE_UNAVAILABLE.name
    details = "Got unexpected error for sending request."


class MaxAttemptsReached(BaseApplicationError):
    status_code = 503
    message = httpx.codes.SERVICE_UNAVAILABLE.name
    details = "Reached max attempt to make action"
