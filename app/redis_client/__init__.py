"""Public interface of the ``app.redis_client`` package.

Use these exports instead of importing ``client`` internals directly. The
module hides the lazy singleton used by response caching, rate lookup caching,
and delivery-job locking.
"""

from app.redis_client.client import close_redis, get_redis

__all__ = (
    "close_redis",
    "get_redis",
)
