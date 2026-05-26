"""Unit tests for parcel schemas."""

from app.schemas import ParcelCreateResponse


def test_parcel_create_response_uses_owner_id() -> None:
    """Expose owner_id instead of the legacy session_id field."""
    response = ParcelCreateResponse(id="parcel-123", owner_id="owner-123")

    assert response.model_dump() == {
        "id": "parcel-123",
        "owner_id": "owner-123",
    }
