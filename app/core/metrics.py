"""Custom Prometheus metrics for business-level observability.

HTTP request metrics are installed by ``prometheus-fastapi-instrumentator`` in
``app.main``. This module defines domain metrics that are easier to alert on:
parcel creation volume and delivery-cost job behavior.
"""

from prometheus_client import Counter, Histogram

PARCELS_CREATED = Counter(
    "parcels_created_total",
    "Total parcels created",
    ["parcel_type"],
)

DELIVERY_RECALC_DURATION = Histogram(
    "delivery_recalc_duration_seconds",
    "Time spent on delivery cost recalculation",
)

DELIVERY_RECALC_PARCELS = Counter(
    "delivery_recalc_parcels_total",
    "Total parcels recalculated",
)
