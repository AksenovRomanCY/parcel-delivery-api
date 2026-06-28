# Microservice Architecture

This document is the fast path for understanding the repository. The code is a
layered FastAPI service: routers validate HTTP input, services hold business
rules, SQLAlchemy models persist state, Redis supports caching/locks/rate limits,
and a separate scheduler process fills delivery costs asynchronously.

## Overview

The Parcel Delivery API follows a layered architecture with these key layers:

* **API Layer (FastAPI Routers)**: HTTP request handling, endpoints grouped by domain (`auth`, `parcels`, `parcel-types`, `tasks`), and middleware integration.
* **Data Schemas (Pydantic)**: Request and response validation, camelCase field formatting, and automatic JSON serialization.
* **Business Logic (Services)**: Core operations on parcels, auth, parcel types, and rate lookup.
* **Data Access Layer (SQLAlchemy)**: Async ORM models, MySQL access, DB constraints, and Alembic migrations.
* **External Integrations**: Fetching USD→RUB rate via Central Bank API using `httpx` and retry logic (`tenacity`).
* **Redis (Cache/Sync/Rate Limits)**: Caching API responses and exchange rates, task coordination via Redis locks, and `limits` counters.
* **Background Scheduler (APScheduler)**: Periodic recalculation of delivery costs in a separate process.
* **Security**: JWT auth by default with rotating HTTP-only refresh cookies, CSRF-protected refresh/logout endpoints, and scope checks; deprecated legacy anonymous sessions can be enabled with `AUTH_REQUIRED=false`; operational task endpoints use `X-Admin-Token`.
* **Observability**: Structured logging, Prometheus metrics, and optional Sentry.
* **Configuration (Pydantic BaseSettings)**: `.env` or environment variable-based configuration for deployment flexibility.

## Project Structure

```
app/
├── api/               # FastAPI routers (auth, health, parcels, parcel_types, tasks)
├── core/              # Settings, logging, cache, security, metrics, Sentry
├── db/                # DB engine/session and FastAPI dependencies
├── models/            # ORM models (Parcel, ParcelType, User, RefreshToken)
├── schemas/           # Pydantic schemas for requests/responses
├── services/          # Business logic (ParcelService, RateService, etc.)
├── tasks/             # Background jobs and scheduler setup
├── middlewares/       # Middleware (e.g., session ID management)
├── main.py            # FastAPI app entry point
├── scheduler_main.py  # APScheduler launch point
```

## Component Diagram

```text
Client
  |
  | HTTP/JSON
  v
FastAPI app
  |
  +-- api/ routers
  |     |
  |     +-- deps.py resolves JWT user_id or legacy session_id
  |     +-- errors.py normalizes JSON error responses
  |
  +-- schemas/ validates input and formats camelCase output
  |
  +-- services/ applies business rules
  |     |
  |     +-- AuthService issues access tokens and refresh cookies
  |     +-- ParcelService owns parcel CRUD rules
  |     +-- RateService fetches and caches USD/RUB rates
  |
  +-- db/ SQLAlchemy AsyncIO sessions
  |     |
  |     v
  |   MySQL
  |
  +-- core/cache.py and core/rate_limit.py
        |
        v
      Redis

Scheduler process
  |
  +-- APScheduler interval job
  +-- Redis lock and rate cache
  +-- MySQL parcel updates
```

## API Layer

* Main app is defined in `main.py`
* Middleware sets deprecated `X-Session-Id` only when `AUTH_REQUIRED=false`
* Routers:

  * `/auth`: register/login and return JWT access tokens
  * `/health`: status check
  * `/parcel-types`: dictionary data
  * `/parcels`: create/list/details
  * `/tasks`: manual task triggers

Response format is standardized using FastAPI’s `response_model`. Error handlers (in `errors.py`) return consistent JSON errors with `code`, `message`, and `details`.

## Database (MySQL + SQLAlchemy)

* Tables: `parcel_type`, `parcel`, `user`, `refresh_token`
* `Parcel` includes: `id`, `name`, `weight_kg`, `declared_value_usd`, `delivery_cost_rub`, `session_id`, `user_id`, `parcel_type_id`
* `User` stores registered credentials and role for JWT mode
* `RefreshToken` stores hashed refresh tokens, token families, expiry, revocation, and rotation metadata
* Monetary and weight values use `Numeric`/`Decimal`, not floats
* DB CHECK constraints enforce positive weight and non-negative money fields
* ORM via `SQLAlchemy AsyncIO`
* DB session managed via FastAPI `Depends`
* Alembic used for schema migrations

## Data Model Sketch

```text
user
  id PK
  email UNIQUE
  hashed_password
  role
  created_at
    |
    | 1..many
    v
refresh_token
  jti PK
  user_id FK -> user.id
  token_hash UNIQUE
  family_id
  expires_at
  revoked_at
  replaced_by_jti
  created_at

parcel_type
  id PK
  name UNIQUE
    |
    | 1..many
    v
parcel
  id PK
  name
  weight_kg
  declared_value_usd
  delivery_cost_rub NULL while pending
  parcel_type_id FK -> parcel_type.id
  user_id FK -> user.id NULL in legacy mode
  session_id used only when AUTH_REQUIRED=false
```

## Services Layer

* `AuthService.register/login(...)`: Creates users, verifies passwords, returns JWTs
* `ParcelService.create_from_dto(...)`: Validates type, weight, links parcel to session or user
* `ParcelService.list_owned(...)`: Returns paginated, filtered parcels
* `ParcelService.get_owned(...)`: Retrieves parcel by ID for current owner, returns or raises `NotFound`/`Unauthorized`
* `RateService.get_usd_rub_rate()`: Fetches USD→RUB, caches in Redis with 10-min TTL, retries via `tenacity`

## Ownership and Authentication

The code supports two ownership modes during the auth migration:

* `AUTH_REQUIRED=true` (default): clients authenticate with `/auth/register` or
  `/auth/login`, receive a short-lived access token plus refresh/CSRF cookies,
  and pass `Authorization: Bearer <token>`; parcel ownership is stored in
  `parcel.user_id`.
* `AUTH_REQUIRED=false` (deprecated): the `assign_session_id` middleware accepts
  or generates `X-Session-Id`, and parcel ownership is stored in
  `parcel.session_id`.

Route dependencies return a generic `owner_id`, so services do not need to know
how the caller was identified. `POST /parcels` returns that same `owner_id` in
its response.

Operational endpoints such as `POST /tasks/recalc-delivery` are not tied to a
user. They require the shared `X-Admin-Token` header and are disabled when
`TASK_ADMIN_TOKEN` is empty.

## Request Flow

Default JWT parcel flow:

```text
Client
  |
  | POST /auth/register or /auth/login
  v
Auth router -> AuthService -> MySQL user/refresh_token
  |
  | access token JSON + refresh/CSRF cookies
  v
Client
  |
  | Authorization: Bearer <access_token>
  | POST /parcels
  v
Parcel router -> get_parcel_writer_owner_id -> decode_token()
  |
  v
ParcelService validates parcel_type and writes parcel.user_id
  |
  v
MySQL commit -> 201 { id, owner_id }
```

Deprecated legacy parcel flow:

```text
Client
  |
  | request without Bearer token, only when AUTH_REQUIRED=false
  v
Session middleware accepts or creates X-Session-Id
  |
  v
Parcel router -> get_session_id()
  |
  v
ParcelService writes parcel.session_id
```

## Redis Caching

* Decorator `@redis_cache(prefix, ttl, key_func)` applies to API functions
* Custom key logic includes either `Authorization` hash or `X-Session-Id` for per-owner cache separation
* Parcel types are cached globally; parcel list/detail responses are cached per owner/query
* Cache invalidation is TTL-based, so asynchronous delivery-cost updates can appear after a short delay

## Background Tasks (APScheduler)

* `recalc_delivery_costs()` (in `tasks/delivery.py`):

  * Acquires Redis lock (NX key `delivery_job_lock`)
  * Loads parcels with `NULL` cost in batches
  * Fetches current USD→RUB rate
  * Applies formula:

    ```
    cost = (0.5 × weight + 0.01 × declaredValueUsd) × rate
    ```
  * Commits updates, logs result
* Runs every `DELIVERY_JOB_INTERVAL_MIN` minutes via `APScheduler`
* Manual trigger via `POST /tasks/recalc-delivery` with `X-Admin-Token`
* Writes `delivery_last_run_updated` and `delivery_last_run_at` metadata to Redis

## Delivery Cost Flow

```text
Scheduler tick or admin trigger
  |
  v
recalc_delivery_costs()
  |
  +-- acquire Redis NX lock: delivery_job_lock
  |
  +-- load pending parcels from MySQL where delivery_cost_rub IS NULL
  |
  +-- RateService.get_usd_rub_rate()
  |     |
  |     +-- read cached rate from Redis, or
  |     +-- fetch Central Bank API with retry and cache result
  |
  +-- calculate RUB cost for each parcel
  |
  +-- commit updates to MySQL
  |
  +-- write last-run metadata to Redis and release lock
```

## Asynchronous Flow

* Entire stack is async: FastAPI, SQLAlchemy, Redis client, HTTP client (`httpx`)
* Uses `async with` for DB sessions, HTTP clients
* `AsyncIOScheduler` with `coalesce=True`, `max_instances=1`

## Session Middleware and JWT

* Assigns deprecated `X-Session-Id` per request if absent (UUID4)
* Saves session to `request.state`
* Includes session plus `Deprecation` and `Sunset` in response headers
* Installed only when `AUTH_REQUIRED=false`
* In JWT mode, `OAuth2PasswordBearer` extracts a token and `decode_token`
  validates issuer, audience, expiration, role, and scopes before returning
  typed claims.

## Refresh Tokens

* Refresh tokens are stored only as SHA-256 hashes in `refresh_token`
* Each login/register creates a new token family
* `POST /auth/refresh` rotates the current token and revokes the previous token
* Reusing a revoked refresh token revokes the entire family
* `POST /auth/logout` revokes the current token
* `POST /auth/logout-all` revokes all refresh tokens for the authenticated user

## Logging

* Format: `%(asctime)s [%(levelname)s] %(name)s - %(message)s`
* Key events include:

  * `parcel_created: parcel=... owner_id=...`
  * `unauthorized_access: parcel_id=... owner_id=...`
  * `delivery_job_done: updated=... rate=...`
  * `new_session_id_assigned: session_id=...`
* Log level controlled via `.env`

## Observability

* `/metrics` is exposed through `prometheus-fastapi-instrumentator` when `ENABLE_METRICS=true`
* Custom counters/histograms live in `app/core/metrics.py`
* Sentry initializes only when `SENTRY_DSN` is set

## Conclusion

Parcel Delivery API is a cloud-ready microservice built for separation of concerns, horizontal scalability, observability, and robustness:

* **Reliable**: Retry logic, Redis locks, DB transactions
* **Performant**: Async, caching, batch updates
* **Maintainable**: Clean layers, type safety, logs

Designed to evolve toward stricter auth requirements, new delivery types, rate strategies, or multi-currency support.
