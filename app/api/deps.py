from fastapi import Request


def get_session_id(request: Request) -> str:
    """Dependency that extracts the session ID from request state.

    Assumes that a middleware has already set ``request.state.session_id``.
    Used to inject the session identifier into route handlers.

    Args:
        request: FastAPI request object with pre-assigned session state.

    Returns:
        str: Session ID as a string.

    Raises:
        AttributeError: If the session ID was not set by middleware.
    """
    return request.state.session_id
