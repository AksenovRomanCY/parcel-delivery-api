"""The public interface of the `app.redis' package."""

from .client import get_redis  # noqa: F401

__all__ = ["get_redis"]
