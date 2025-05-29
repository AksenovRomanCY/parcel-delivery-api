# Microservice Architecture

This section describes the internal architecture of the Parcel Delivery API: the components it consists of, how data flows from request to database, what background processes exist, and what patterns are used for structure, logging, responses, async operations, and caching.

## Overview

The Parcel Delivery API follows a layered architecture with these key layers:

* **API Layer (FastAPI Routers)**: HTTP request handling, endpoints grouped by domain (`parcels`, `parcel-types`, `tasks`), and middleware integration.
* **Data Schemas (Pydantic)**: Request and response validation, camelCase field formatting, and automatic JSON serialization.
* **Business Logic (Services)**: Core operations on parcels and types, input validation, orchestration of calculations.
* **Data Access Layer (SQLAlchemy)**: Async ORM models, database access via MySQL, with Alembic for migrations.
* **External Integrations**: Fetching USD→RUB rate via Central Bank API using `httpx` and retry logic (`tenacity`).
* **Redis (Cache/Queue/Sync)**: Caching API responses and exchange rates, task coordination via Redis locks.
* **Background Scheduler (APScheduler)**: Periodic recalculation of delivery costs in a separate process.
* **Logging & Monitoring**: Structured logging using `logging` (stdout + formatted key=value messages).
* **Configuration (Pydantic BaseSettings)**: `.env` or environment variable-based configuration for deployment flexibility.

## Project Structure

```
app/
├── api/               # FastAPI routers (endpoints: health, parcels, parcel_types, tasks)
├── core/              # Core config, logging setup, cache decorators
├── db/                # DB engine/session and FastAPI dependencies
├── models/            # ORM models (Parcel, ParcelType)
├── schemas/           # Pydantic schemas for requests/responses
├── services/          # Business logic (ParcelService, RateService, etc.)
├── tasks/             # Background jobs and scheduler setup
├── middlewares/       # Middleware (e.g., session ID management)
├── main.py            # FastAPI app entry point
├── scheduler_main.py  # APScheduler launch point
```

## API Layer

* Main app is defined in `main.py`
* Middleware sets `X-Session-Id` per request
* Routers:

  * `/health`: status check
  * `/parcel-types`: dictionary data
  * `/parcels`: create/list/details
  * `/tasks`: manual task triggers (dev only)

Response format is standardized using FastAPI’s `response_model`. Error handlers (in `errors.py`) return consistent JSON errors with `code`, `message`, and `details`.

## Database (MySQL + SQLAlchemy)

* Tables: `parcel_type`, `parcel`
* `Parcel` includes: `id`, `name`, `weight_kg`, `declared_value_usd`, `delivery_cost_rub`, `session_id`, `parcel_type_id`
* ORM via `SQLAlchemy AsyncIO`
* DB session managed via FastAPI `Depends`
* Alembic used for schema migrations

## Services Layer

* `ParcelService.create_from_dto(...)`: Validates type, weight, links parcel to session
* `ParcelService.list_owned(...)`: Returns paginated, filtered parcels
* `ParcelService.get_owned(...)`: Retrieves parcel by ID for current session, returns or raises `NotFound`
* `RateService.get_usd_rub_rate()`: Fetches USD→RUB, caches in Redis with 10-min TTL, retries via `tenacity`

## Redis Caching

* Decorator `@redis_cache(prefix, ttl, key_func)` applies to API functions
* Custom key logic includes/excludes session ID for per-user cache separation
* Parcel types cached globally (60s TTL), parcel list cached per session (60s)

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
* Runs every 5 min via `APScheduler`
* Manual trigger via `POST /tasks/recalc-delivery`

## Asynchronous Flow

* Entire stack is async: FastAPI, SQLAlchemy, Redis client, HTTP client (`httpx`)
* Uses `async with` for DB sessions, HTTP clients
* `AsyncIOScheduler` with `coalesce=True`, `max_instances=1`

## Session Middleware

* Assigns `X-Session-Id` per request if absent (UUID4)
* Saves session to `request.state`
* Includes session in response headers
* Used in cache keys and service methods

## Logging

* Format: `%(asctime)s [%(levelname)s] %(name)s - %(message)s`
* Key events include:

  * `parcel_created: parcel=... session_id=...`
  * `unauthorized_access: parcel_id=... session_id=...`
  * `delivery_job_done: updated=... rate=...`
  * `new_session_id_assigned: session_id=...`
* Log level controlled via `.env`

## Conclusion

Parcel Delivery API is a cloud-ready microservice built for separation of concerns, horizontal scalability, observability, and robustness:

* **Reliable**: Retry logic, Redis locks, DB transactions
* **Performant**: Async, caching, batch updates
* **Maintainable**: Clean layers, type safety, logs

Designed to evolve toward features like user auth, new delivery types, rate strategies, or multi-currency support.
