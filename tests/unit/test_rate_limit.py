"""Unit tests for rate-limit response helpers."""

import json
from collections.abc import Callable

import pytest
from starlette.requests import Request

from app.core.rate_limit import RateLimitExceeded, rate_limit_exceeded_handler

RequestFactory = Callable[..., Request]


@pytest.mark.asyncio
async def test_rate_limit_exceeded_handler_returns_stable_json(
    request_factory: RequestFactory,
) -> None:
    """Rate-limit failures should keep the public 429 JSON shape stable."""
    # Arrange
    request = request_factory()
    exc = RateLimitExceeded("20 per 1 minute")

    # Act
    response = await rate_limit_exceeded_handler(request, exc)

    # Assert
    assert response.status_code == 429
    assert json.loads(bytes(response.body)) == {
        "error": "Rate limit exceeded: 20 per 1 minute",
    }
