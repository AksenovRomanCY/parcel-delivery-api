# Parcel Delivery API

**Parcel Delivery API** is a microservice for registering and tracking parcel deliveries. The service allows anonymous registration of parcels, automatically calculates delivery cost in Russian rubles based on weight and declared value in USD, periodically updates exchange rates, and provides an API to retrieve parcel types and track registered shipments.

## Core Functionality

- **Parcel Registration**: A user (identified via session) can register a new parcel by providing a name, weight, declared value in USD, and parcel type. The service assigns a unique ID and asynchronously calculates the delivery cost in RUB.
- **Retrieving Parcel Types**: A reference list of parcel types (e.g., clothing, electronics, other) is available via the API, intended for UI dropdowns and filters.
- **List of Parcels**: Users can fetch a list of their parcels (per session), with filtering by type and presence of delivery cost, along with pagination.
- **Parcel Details**: Each registered parcel includes detailed information, including the calculated delivery cost once it becomes available.
- **Background Tasks**: The service periodically recalculates delivery costs for new parcels and caches the current USD/RUB exchange rate. A manual endpoint is available for triggering background tasks.

## Technology Stack

| Component             | Technology                                                  |
|-----------------------|-------------------------------------------------------------|
| Language & Framework  | Python 3.13, FastAPI (asynchronous web framework)           |
| Database              | MySQL 8 via SQLAlchemy 2 AsyncIO ORM, with Alembic migrations |
| Cache & Sync          | Redis 7 (caching dictionaries, exchange rates, locking)     |
| Background Tasks      | APScheduler (recalculates delivery costs every 5 minutes)   |
| Validation & Schemas  | Pydantic 2 (BaseModel for input/output validation)          |
| Logging               | Structured logging, unified across libraries like Uvicorn and SQLAlchemy |

## GitHub

[GitHub Repository](https://github.com/AksenovRomanCY/parcel-delivery-api)

## Documentation

Full documentation is located in the `docs/` directory. Key sections include:

- **Installation**: `docs/INSTALLATION.md` – how to deploy the service (via Docker Compose) and configure environment variables.
- **API Usage**: `docs/USAGE.md` – overview of REST API (endpoints, example requests, Swagger UI).
- **Testing**: `docs/TESTING.md` – how to run tests, test infrastructure overview, and coverage measurement.
- **Architecture**: `docs/ARCHITECTURE.md` – internal design of the microservice (modules, layers, DB/cache/task scheduler interaction).

## Quick Start

To run the application locally, you need **Docker** and **Docker Compose**.

### 1. Clone the repository

```bash
git clone https://github.com/your-org/parcel-delivery-api.git && cd parcel-delivery-api
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit .env as required (e.g., set the DB password). See docs/INSTALLATION.md for all options.

### 3. Launch the service with Docker Compose

```bash
docker-compose up --build
```

This will:
- Build the Docker image
- Launch containers for the API, scheduler, MySQL, and Redis
- Apply Alembic migrations on first run
- Populate initial reference data

### 4. Access the API

Once running, the API listens on port 8000. Open:

```bash
http://localhost:8000/docs
```

to access Swagger UI (interactive API documentation).

### 5. Health check

You can check the service health with:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok"}
```
