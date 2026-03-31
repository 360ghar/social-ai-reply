"""Custom exception hierarchy for RedditFlow API.

These map to structured HTTP responses via the global exception handler in main.py.
"""


class AppException(Exception):
    """Base exception for all application errors."""

    status_code: int = 500
    detail: str = "Internal server error"


class NotFoundError(AppException):
    status_code = 404
    detail = "Resource not found."


class ForbiddenError(AppException):
    status_code = 403
    detail = "You do not have access to this resource."


class ConflictError(AppException):
    status_code = 409
    detail = "Resource already exists."


class AuthenticationError(AppException):
    status_code = 401
    detail = "Authentication required."


class BusinessRuleError(AppException):
    """For state machine violations like invalid opportunity transitions."""

    status_code = 422
    detail = "Operation violates a business rule."


class RateLimitError(AppException):
    status_code = 429
    detail = "Too many requests."


class ValidationError(AppException):
    status_code = 422
    detail = "Validation error."
