"""Reusable OpenAPI examples for API route documentation."""

TOKEN_RESPONSE_EXAMPLE = {
    "access_token": (  # nosec B105
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiI0M2Y0YTgyYS1iYjNmLTQ4MzgtOWI4Ni1hOWY1MjZmNTE5N2IifQ."
        "signature"
    ),
    "token_type": "bearer",  # nosec B105
}

VALIDATION_ERROR_EXAMPLE = {
    "code": "validation_error",
    "message": "Payload validation failed",
    "details": [
        {
            "type": "greater_than",
            "loc": ["body", "weightKg"],
            "msg": "Input should be greater than 0",
            "input": "-1",
            "ctx": {"gt": 0},
        }
    ],
}

UNAUTHORIZED_ERROR_EXAMPLE = {
    "code": "unauthorized",
    "message": "Missing authorization token",
    "details": None,
}

FORBIDDEN_ERROR_EXAMPLE = {
    "code": "forbidden",
    "message": "Manual task trigger is disabled",
    "details": None,
}

BUSINESS_ERROR_EXAMPLE = {
    "code": "business_error",
    "message": "Unknown parcel type",
    "details": None,
}

PARCEL_TYPE_LIST_EXAMPLE = {
    "items": [
        {
            "id": "b5e96576-3e2b-4bd7-8d6c-7f0cdd3e5a6e",
            "name": "clothes",
        },
        {
            "id": "a3a814f4-4724-4947-b6ab-8337f3b33969",
            "name": "electronics",
        },
        {
            "id": "9d7b3c28-80b3-4f08-8b22-4a81ec1f0b75",
            "name": "misc",
        },
    ],
    "total": 3,
    "limit": 20,
    "offset": 0,
}

PARCEL_CREATE_RESPONSE_EXAMPLE = {
    "id": "99e93aee-776d-4bc5-8157-ab80a12b6556",
    "owner_id": "c83e529a-9fa9-4445-a2f5-508e2f10e3de",
}

PARCEL_DETAIL_EXAMPLE = {
    "id": "99e93aee-776d-4bc5-8157-ab80a12b6556",
    "name": "Apple iPhone 15 Pro",
    "weightKg": "1.200",
    "declaredValueUsd": "1299.99",
    "deliveryCostRub": None,
    "parcelType": {
        "id": "a3a814f4-4724-4947-b6ab-8337f3b33969",
        "name": "electronics",
    },
}

PARCEL_LIST_EXAMPLE = {
    "items": [PARCEL_DETAIL_EXAMPLE],
    "total": 1,
    "limit": 20,
    "offset": 0,
}

NOT_FOUND_ERROR_EXAMPLE = {"detail": "Not found"}

PARCEL_FORBIDDEN_EXAMPLE = {"detail": "Forbidden"}

TASK_RECALC_RESPONSE_EXAMPLE = {"updated": 5}
