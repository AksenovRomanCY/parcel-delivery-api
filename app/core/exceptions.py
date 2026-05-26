"""Domain exceptions mapped to stable HTTP error responses."""


class BusinessError(ValueError):
    """Business rule violation that should be returned as HTTP 400."""


class NotFoundError(ValueError):
    """Record is missing or intentionally hidden from the caller → HTTP 404."""


class UnauthorizedError(ValueError):
    """Missing or invalid credentials/session identifier → HTTP 401."""


class ForbiddenError(ValueError):
    """Access to resource is denied → HTTP 403."""
