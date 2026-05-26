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
* **Redis (Cache/Sync/Rate Limits)**: Caching API responses and exchange rates, task coordination via Redis locks, and slowapi counters.
* **Background Scheduler (APScheduler)**: Periodic recalculation of delivery costs in a separate process.
* **Security**: Legacy anonymous sessions or JWT auth controlled by `AUTH_REQUIRED`; operational task endpoints use `X-Admin-Token`.
* **Observability**: Structured logging, Prometheus metrics, and optional Sentry.
* **Configuration (Pydantic BaseSettings)**: `.env` or environment variable-based configuration for deployment flexibility.

## Project Structure

```
app/
├── api/               # FastAPI routers (auth, health, parcels, parcel_types, tasks)
├── core/              # Settings, logging, cache, security, metrics, Sentry
├── db/                # DB engine/session and FastAPI dependencies
├── models/            # ORM models (Parcel, ParcelType, User)
├── schemas/           # Pydantic schemas for requests/responses
├── services/          # Business logic (ParcelService, RateService, etc.)
├── tasks/             # Background jobs and scheduler setup
├── middlewares/       # Middleware (e.g., session ID management)
├── main.py            # FastAPI app entry point
├── scheduler_main.py  # APScheduler launch point
```

## API Layer

* Main app is defined in `main.py`
* Middleware sets `X-Session-Id` only when `AUTH_REQUIRED=false`
* Routers:

  * `/auth`: register/login and return JWT access tokens
  * `/health`: status check
  * `/parcel-types`: dictionary data
  * `/parcels`: create/list/details
  * `/tasks`: manual task triggers

Response format is standardized using FastAPI’s `response_model`. Error handlers (in `errors.py`) return consistent JSON errors with `code`, `message`, and `details`.

## Database (MySQL + SQLAlchemy)

* Tables: `parcel_type`, `parcel`, `user`
* `Parcel` includes: `id`, `name`, `weight_kg`, `declared_value_usd`, `delivery_cost_rub`, `session_id`, `user_id`, `parcel_type_id`
* Monetary and weight values use `Numeric`/`Decimal`, not floats
* DB CHECK constraints enforce positive weight and non-negative money fields
* ORM via `SQLAlchemy AsyncIO`
* DB session managed via FastAPI `Depends`
* Alembic used for schema migrations

## Services Layer

* `AuthService.register/login(...)`: Creates users, verifies passwords, returns JWTs
* `ParcelService.create_from_dto(...)`: Validates type, weight, links parcel to session or user
* `ParcelService.list_owned(...)`: Returns paginated, filtered parcels
* `ParcelService.get_owned(...)`: Retrieves parcel by ID for current owner, returns or raises `NotFound`/`Unauthorized`
* `RateService.get_usd_rub_rate()`: Fetches USD→RUB, caches in Redis with 10-min TTL, retries via `tenacity`

## Ownership and Authentication

The code supports two ownership modes:

* `AUTH_REQUIRED=false` (default): the `assign_session_id` middleware accepts or
  generates `X-Session-Id`, and parcel ownership is stored in `parcel.session_id`.
* `AUTH_REQUIRED=true`: clients authenticate with `/auth/register` or `/auth/login`
  and pass `Authorization: Bearer <token>`; parcel ownership is stored in
  `parcel.user_id`.

Route dependencies return a generic `owner_id`, so services do not need to know
how the caller was identified. `POST /parcels` returns that same `owner_id` in
its response.

Operational endpoints such as `POST /tasks/recalc-delivery` are not tied to a
user. They require the shared `X-Admin-Token` header and are disabled when
`TASK_ADMIN_TOKEN` is empty.

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

## Asynchronous Flow

* Entire stack is async: FastAPI, SQLAlchemy, Redis client, HTTP client (`httpx`)
* Uses `async with` for DB sessions, HTTP clients
* `AsyncIOScheduler` with `coalesce=True`, `max_instances=1`

## Session Middleware and JWT

* Assigns `X-Session-Id` per request if absent (UUID4)
* Saves session to `request.state`
* Includes session in response headers
* Installed only when `AUTH_REQUIRED=false`
* In JWT mode, `OAuth2PasswordBearer` extracts a token and `decode_token` returns the user ID

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
