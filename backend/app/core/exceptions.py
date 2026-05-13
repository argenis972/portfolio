"""
Custom application exceptions.

Defines an exception hierarchy for consistent error handling.
Each exception maps to a specific HTTP status code.
"""


class DomainError(Exception):
    """
    Base exception for business rule errors.

    Maps to HTTP 400 Bad Request.
    Used when the request violates domain rules.

    Attributes:
        message: Description of the error.
        code: Internal code for tracking (optional).
    """

    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code or "DOMAIN_ERROR"
        super().__init__(message)


class ValidationError(DomainError):
    """
    Exception for data validation errors.

    Maps to HTTP 422 Unprocessable Entity.
    Used when data does not pass business validations.

    Example:
        raise ValidationError("Invalid email", code="INVALID_EMAIL")
    """

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code or "VALIDATION_ERROR")


class InfrastructureError(Exception):
    """
    Exception for external infrastructure errors.

    Maps to HTTP 500 Internal Server Error.
    Used when communication with external systems fails
    (files, APIs, database, etc.).

    Attributes:
        message: Description of the error.
        code: Internal code.
        origin: System that caused the error (optional).
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        origin: str | None = None,
    ) -> None:
        self.message = message
        self.code = code or "INFRASTRUCTURE_ERROR"
        self.origin = origin
        super().__init__(message)


class ResourceNotFoundError(DomainError):
    """
    Exception for resource not found.

    Maps to HTTP 404 Not Found.
    Used when the requested resource does not exist.

    Example:
        raise ResourceNotFoundError(
            "Project not found",
            code="PROJECT_NOT_FOUND"
        )
    """


class MissingIdempotencyKeyError(DomainError):
    """
    Exception for missing Idempotency-Key in protected routes.

    Maps to HTTP 400 Bad Request.
    """

    def __init__(self, message: str = "Header 'Idempotency-Key' is required") -> None:
        super().__init__(message, code="MISSING_IDEMPOTENCY_KEY")


class DuplicateContactError(DomainError):
    """
    Raised when an identical contact message is submitted within the dedup window.

    Maps to HTTP 400 Bad Request.
    Replaces the ad-hoc JSONResponse in the contact controller, ensuring all
    error responses go through the global domain_error_handler for a uniform
    API contract: {"error": {"code": "DUPLICATE_CONTENT", "message": "..."}}.
    """

    def __init__(self) -> None:
        super().__init__(
            message="Duplicate message detected. Please wait before sending again.",
            code="DUPLICATE_CONTENT",
        )
