class BusinessError(ValueError):
    """Business logic errors that should be given to the c HTTP 400 client."""


class NotFoundError(ValueError):
    """Exception “record isn't found” → HTTP 404."""


class UnauthorizedError(ValueError):
    """Missing or invalid session ID → HTTP 401."""


class ForbiddenError(ValueError):
    """Access to resource is denied → HTTP 403."""
