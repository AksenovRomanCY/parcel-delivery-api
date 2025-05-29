# API Usage

This section describes how to work with the Parcel Delivery API: key endpoints, request/response examples, and behavior. Once the application is running, use Swagger UI at [http://localhost:8000/docs](http://localhost:8000/docs) to explore and test the API interactively.

---

## Endpoint Overview

* **Swagger UI**: `GET /docs` – Interactive documentation for all routes and data schemas.
* **Health Check**: `GET /health` – Always returns `{ "status": "ok" }` with status code 200 (used for uptime monitoring).

### Main REST API Resources

* `GET /parcel-types` – Retrieve all available parcel types.
* `POST /parcels` – Register a new parcel with specified attributes.
* `GET /parcels` – List all parcels created in the current session (with filtering & pagination).
* `GET /parcels/{id}` – Get detailed information about a specific parcel (if owned by session).
* `POST /tasks/recalc-delivery` – Manually trigger background recalculation of delivery costs (for debugging/admin).

---

## Session Identification (X-Session-Id)

There is no authentication in the service. Each parcel is tied to an **anonymous session**, identified by the `X-Session-Id` header. If the header is not provided, the API generates a new UUID and returns it in the response header.

Clients must retain and reuse this session ID in subsequent requests. Otherwise, each request will be treated as a new session and won't see previously created parcels.

---

## Request and Response Format

The API uses **JSON** for both requests and responses. All responses follow a standard structure:

* On success: data is returned (either an object or a list)
* On error: JSON with `code`, `message`, and optional `details`

All response models use **camelCase** for JSON fields. Example: `weight_kg` in Python becomes `weightKg` in JSON, using Pydantic alias generator for frontend compatibility.

---

## GET /parcel-types

Returns a list of available parcel types. Used for dropdowns or filtering UI.

### Query Parameters:

* `limit` – Records per page (1–100, default: 20)
* `offset` – Records to skip (default: 0)

### Example Request:

```http
GET /parcel-types?limit=20&offset=0 HTTP/1.1
Host: localhost:8000
```

### Example Response:

```json
{
  "items": [
    { "id": "...", "name": "clothes" },
    { "id": "...", "name": "electronics" }
  ],
  "total": 3,
  "limit": 20,
  "offset": 0
}
```

> Cached for 60 seconds. Parcel types rarely change.

---

## POST /parcels

Registers a new parcel.

### Request Body:

```json
{
  "name": "Apple iPhone 15 Pro",
  "weightKg": 1.2,
  "declaredValueUsd": 1299.99,
  "parcelTypeId": "..."
}
```

* `name`: Description
* `weightKg`: Must be > 0
* `declaredValueUsd`: ≥ 0
* `parcelTypeId`: Valid UUID from `/parcel-types`

### On Success:

```json
{
  "id": "...",
  "session_id": "..."
}
```

> Delivery cost is calculated asynchronously (initially `null`).

---

## GET /parcels

Returns all parcels for the current session.

### Query Parameters:

* `limit`: 1–100 (default: 20)
* `offset`: starting index (default: 0)
* `type_id`: filter by parcel type UUID
* `has_cost`: `true` or `false` (filter by delivery cost presence)

### Example Request:

```http
GET /parcels?limit=10&offset=0&has_cost=false HTTP/1.1
X-Session-Id: ...
```

### Example Response:

```json
{
  "items": [
    {
      "id": "...",
      "name": "Apple iPhone 15 Pro",
      "weightKg": 1.2,
      "declaredValueUsd": 1299.99,
      "deliveryCostRub": null,
      "parcelType": {
        "id": "...",
        "name": "electronics"
      }
    }
  ],
  "total": 5,
  "limit": 10,
  "offset": 0
}
```

> Results are cached for 60 seconds per session. Use polling to check when cost is calculated.

---

## GET /parcels/{id}

Returns a single parcel by ID if it belongs to the current session.

### Example:

```http
GET /parcels/{id} HTTP/1.1
X-Session-Id: ...
```

### Example Response:

```json
{
  "id": "...",
  "name": "Apple iPhone 15 Pro",
  "weightKg": 1.2,
  "declaredValueUsd": 1299.99,
  "deliveryCostRub": 75420.0,
  "parcelType": {
    "id": "...",
    "name": "electronics"
  }
}
```

> Returns `404` if not found or session mismatch.

---

## POST /tasks/recalc-delivery

Manually trigger delivery cost recalculation.

* No body required.
* Returns number of parcels updated.

### Example:

```http
POST /tasks/recalc-delivery HTTP/1.1
```

### Response:

```json
{ "updated": 5 }
```

> Usually handled by background jobs. Use in test/admin scenarios only.

---

## Error Handling

The service uses standardized error responses:

* `400 Bad Request` — Business logic violation
* `404 Not Found` — Resource missing or session mismatch
* `422 Unprocessable Entity` — Validation failure
* `500 Internal Server Error` — Unexpected server error

### Example Error:

```json
{
  "code": "validation_error",
  "message": "Payload validation failed",
  "details": [ ... ]
}
```

Logs (WARNING / ERROR) are available for server-side diagnostics.

---

Start your API exploration with Swagger UI at [http://localhost:8000/docs](http://localhost:8000/docs).
