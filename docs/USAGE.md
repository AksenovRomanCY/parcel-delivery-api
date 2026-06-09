# API Usage

This section describes how to work with the Parcel Delivery API: key endpoints, request/response examples, and behavior. Once the application is running, use Swagger UI at [http://localhost:8000/docs](http://localhost:8000/docs) to explore and test the API interactively.

---

## Endpoint Overview

* **Swagger UI**: `GET /docs` – Interactive documentation for all routes and data schemas.
* **Health Check**: `GET /health` – Always returns `{ "status": "ok" }` with status code 200 (used for uptime monitoring).
* **Metrics**: `GET /metrics` – Prometheus-compatible metrics when `ENABLE_METRICS=true`.

### Main REST API Resources

* `POST /auth/register` – Create a user and receive a JWT access token.
* `POST /auth/login` – Authenticate and receive a JWT access token.
* `GET /parcel-types` – Retrieve all available parcel types.
* `POST /parcels` – Register a new parcel with specified attributes.
* `GET /parcels` – List all parcels owned by the authenticated user (with filtering & pagination).
* `GET /parcels/{id}` – Get detailed information about a specific parcel (if owned by the caller).
* `POST /tasks/recalc-delivery` – Manually trigger background recalculation of delivery costs (for debugging/admin).

---

## Caller Identification

The service uses JWT Bearer authentication by default (`AUTH_REQUIRED=true`).

Clients call `/auth/register` or `/auth/login`, then send
`Authorization: Bearer <token>` for parcel endpoints. Parcel ownership is based
on the JWT subject.

The legacy anonymous `X-Session-Id` flow is still available only when
`AUTH_REQUIRED=false`. That mode is deprecated and responses include
`Deprecation` and `Sunset` headers.

---

## Request and Response Format

The API uses **JSON** for both requests and responses. All responses follow a standard structure:

* On success: data is returned (either an object or a list)
* On error: JSON with `code`, `message`, and optional `details`

All response models use **camelCase** for JSON fields. Example: `weight_kg` in Python becomes `weightKg` in JSON, using Pydantic alias generator for frontend compatibility.

---

## POST /auth/register

Registers a user and returns a JWT access token.

```json
{
  "email": "user@example.com",
  "password": "securepass123"
}
```

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

## POST /auth/login

Authenticates an existing user and returns the same token response shape as
registration.

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

Requires `Authorization: Bearer <token>`.

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
  "owner_id": "..."
}
```

> `owner_id` is the user ID in the default JWT mode.
> Delivery cost is calculated asynchronously (initially `null`).

---

## GET /parcels

Returns all parcels for the authenticated user.

### Query Parameters:

* `limit`: 1–100 (default: 20)
* `offset`: starting index (default: 0)
* `type_id`: filter by parcel type UUID
* `has_cost`: `true` or `false` (filter by delivery cost presence)

### Example Request:

```http
GET /parcels?limit=10&offset=0&has_cost=false HTTP/1.1
Authorization: Bearer ...
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

> Results are cached briefly per caller/query. Use polling to check when cost is calculated.

---

## GET /parcels/{id}

Returns a single parcel by ID if it belongs to the current session/user.

### Example:

```http
GET /parcels/{id} HTTP/1.1
Authorization: Bearer ...
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

> Returns `404` if not found and `403` if the parcel exists but belongs to another caller.

---

## POST /tasks/recalc-delivery

Manually trigger delivery cost recalculation.

* No body required.
* Requires `X-Admin-Token` matching `TASK_ADMIN_TOKEN`.
* Returns number of parcels updated.

### Example:

```http
POST /tasks/recalc-delivery HTTP/1.1
X-Admin-Token: ...
```

### Response:

```json
{ "updated": 5 }
```

> Usually handled by background jobs. If `TASK_ADMIN_TOKEN` is empty, manual
> triggering is disabled and the endpoint returns `403`.

---

## Error Handling

The service uses standardized error responses:

* `400 Bad Request` — Business logic violation
* `401 Unauthorized` — Missing/invalid session or JWT
* `403 Forbidden` — Caller is authenticated/identified but cannot access the resource
* `404 Not Found` — Resource missing
* `422 Unprocessable Entity` — Validation failure
* `429 Too Many Requests` — Rate limit exceeded
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
