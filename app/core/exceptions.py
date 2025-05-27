class BusinessError(ValueError):
    """Business logic errors that should be given to the c HTTP 400 client."""


class NotFoundError(ValueError):
    """Exception “record isn't found” → HTTP 404."""
