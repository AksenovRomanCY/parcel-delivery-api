"""Session ID middleware.

Ensures that every incoming HTTP request has a session identifier
attached, even if the client is anonymous. The session ID is stored in
the request state and propagated back in the response headers.
"""

import logging
from uuid import UUID, uuid4

from fastapi import Request, Response

SESSION_HEADER = "X-Session-Id"

log = logging.getLogger(__name__)


async def assign_session_id(request: Request, call_next):
    """Attach a session ID to the request and propagate it in the response.

    The middleware checks for an existing ``X-Session-Id`` header.
    If not present, it generates a new UUID. The ID is stored in
    ``request.state.session_id`` for downstream business logic, and the
    same header is included in the response for client reuse.

    Args:
        request: Incoming HTTP request object.
        call_next: ASGI handler for the next processing step.

    Returns:
        Response: HTTP response with ``X-Session-Id`` header included.
    """
    # Use client-provided session ID if available; otherwise, generate one.
    session = request.headers.get(SESSION_HEADER)
    if not session:
        session = str(uuid4())
        log.debug("new_session_id_assigned: session_id=%s", session)
    else:
        try:
            UUID(session)
        except ValueError:
            log.warning("invalid_session_id_format: session_id=%s", session)
            session = str(uuid4())
            log.debug("new_session_id_assigned: session_id=%s", session)

    # Store the session ID in request state so app code can access it.
    request.state.session_id = session

    # Forward request to the next component in the ASGI pipeline.
    response: Response = await call_next(request)

    # Reflect the session ID in the response header.
    response.headers[SESSION_HEADER] = session

    return response
