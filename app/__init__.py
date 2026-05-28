"""Top-level package entrypoint for the parcel delivery API.

Importing ``app`` from this package gives ASGI servers, tests, and small
scripts the fully composed FastAPI application from :mod:`app.main`. Keep
runtime wiring in ``app.main`` and use this module only as the stable import
surface, for example ``uvicorn app:app``.
"""

from app.main import app

__all__ = ("app",)
