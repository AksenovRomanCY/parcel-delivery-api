"""Unit tests for custom Prometheus metrics."""

import pytest
from prometheus_client import Counter, Histogram

from app.core.metrics import (
    DELIVERY_RECALC_DURATION,
    DELIVERY_RECALC_PARCELS,
    PARCELS_CREATED,
)


@pytest.mark.parametrize(
    ("metric", "expected_type"),
    [
        (PARCELS_CREATED, Counter),
        (DELIVERY_RECALC_DURATION, Histogram),
        (DELIVERY_RECALC_PARCELS, Counter),
    ],
)
def test_metrics_have_expected_types(
    metric: Counter | Histogram,
    expected_type: type[Counter] | type[Histogram],
) -> None:
    """Custom metrics should use the expected Prometheus metric types."""
    # Arrange

    # Act
    is_expected_type = isinstance(metric, expected_type)

    # Assert
    assert is_expected_type


def test_parcels_created_accepts_parcel_type_label() -> None:
    """PARCELS_CREATED should accept the parcel_type label."""
    # Arrange
    labels = PARCELS_CREATED.labels(parcel_type="test-type")

    # Act
    labels.inc()

    # Assert
    assert labels is PARCELS_CREATED.labels(parcel_type="test-type")
