"""Unit tests for custom Prometheus metrics."""

from prometheus_client import Counter, Histogram

from app.core.metrics import (
    DELIVERY_RECALC_DURATION,
    DELIVERY_RECALC_PARCELS,
    PARCELS_CREATED,
)


def test_parcels_created_is_counter():
    assert isinstance(PARCELS_CREATED, Counter)


def test_delivery_recalc_duration_is_histogram():
    assert isinstance(DELIVERY_RECALC_DURATION, Histogram)


def test_delivery_recalc_parcels_is_counter():
    assert isinstance(DELIVERY_RECALC_PARCELS, Counter)


def test_parcels_created_accepts_parcel_type_label():
    PARCELS_CREATED.labels(parcel_type="test-type").inc()
