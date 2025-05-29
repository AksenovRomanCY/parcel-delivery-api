# Installation & Deployment

This section describes how to deploy the **Parcel Delivery API** microservice using Docker and Docker Compose, including environment variable configuration.

## Prerequisites

- **Docker & Docker Compose**: Ensure Docker is installed and running. Docker Compose version **3.8+** is required (as specified in `docker-compose.yml`).
- **Source Code**: Clone the project repository:

```bash
git clone https://github.com/AksenovRomanCY/parcel-delivery-api.git && cd parcel-delivery-api
```

## Environment Configuration (.env)
The application uses a .env file (in the project root) for configuration. An example file .env.example is provided in the repo. Copy and adjust it:

```bash
cp .env.example .env
```

### MySQL Database Settings
- **DB_PROTOCOL** – Database connection protocol (default: mysql+aiomysql)
- **DB_USER** – DB username (default: root)
- **DB_PASSWORD** – DB password (default: root)
- **DB_HOST** – DB host (default: db, the container name)
- **DB_PORT** – DB port (default: 3306)
- **DB_NAME** – DB name (default: delivery)

### Redis Settings
- **REDIS_HOST** – Redis host (default: redis, the container name)
- **REDIS_PORT** – Redis port (default: 6379)
- **REDIS_PASS** – Redis password (default: yourstrongpass, change in production)
- **REDIS_BIND** – Redis bind IP (default: 0.0.0.0)
- **REDIS_PROTECTED** – Enable Redis protected mode (default: yes)

### Other Settings
- **LOG_LEVEL** – Logging level (default: INFO; options: DEBUG, INFO, WARNING, ERROR)
- **ENVIRONMENT** – Runtime environment (default: prod, can be set to dev to enable debug features)

## Example .env File
```ini
DB_PROTOCOL=mysql+aiomysql
DB_USER=root
DB_PASSWORD=root
DB_HOST=db
DB_PORT=3306
DB_NAME=delivery

REDIS_HOST=redis
REDIS_BIND=0.0.0.0
REDIS_PROTECTED=yes
REDIS_PORT=6379
REDIS_PASS=yourstrongpass

LOG_LEVEL=INFO
ENVIRONMENT=prod
```

Note: Default values in .env.example are suitable for running via Docker Compose. For production, use secure passwords and adjust the configuration as needed.

## Launching
The docker-compose.yml file defines four services:

- app: The main FastAPI application (Uvicorn on port 8000)
- scheduler: Background task scheduler (runs periodic jobs)
- db: MySQL 8.0 database
- redis: Redis server (cache and synchronization)

To start all components:
```bash
docker-compose up -d --build
```

This will:
- Build the application image from the Dockerfile
- Start all containers in detached mode
- Wait for MySQL readiness (via healthcheck)
- Automatically apply Alembic migrations on first start:
  - Creates tables parcel_type and parcel
  - Loads initial parcel types: clothes, electronics, misc

## Post-Launch
After successful startup:
- The FastAPI app is available at http://localhost:8000
- The scheduler starts periodic tasks in the background
- MySQL is initialized with schema and test data
- Redis is ready to accept connections

## Health Check
Verify service health:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok"}
```

## Swagger UI
Open in your browser:
```bash
http://localhost:8000/docs
```
This provides interactive documentation for exploring and testing the API.

## Stopping and Cleaning Up
To stop running containers:
```bash
docker-compose down
```

MySQL data is preserved in the db_data volume.

To remove all data and reset the state:
```bash
docker-compose down -v
```
This will delete the volume and reinitialize the DB on next startup with default reference data.
