from uuid import uuid4

from fastapi import Request, Response

from app import app

SESSION_HEADER = "X-Session-Id"


@app.middleware("http")
async def assign_session_id(request: Request, call_next):
    """Attach a session ID to both the incoming request and outgoing response.

    The middleware reads the ``X-Session-Id`` header from the request.
    If it is missing, a new UUID is generated. The identifier is stored in
    ``request.state.session_id`` for downstream business logic.
    Finally, the same header is added to the response so the client keeps
    the session context.

    Args:
        request: Incoming HTTP request.
        call_next: ASGI callable that processes the request and returns a
            response.

    Returns:
        fastapi.Response: HTTP response with the ``X-Session-Id`` header
            set.
    """
    session_id = request.headers.get(SESSION_HEADER) or str(uuid4())
    request.state.session_id = session_id

    response: Response = await call_next(request)
    response.headers[SESSION_HEADER] = session_id
    return response
