# Running Tests

Test configuration lives in `pyproject.toml` under `[tool.pytest.ini_options]`.
The suite is split into fast unit tests and integration tests that require MySQL
and Redis.

## Unit Tests

Run the unit suite when you do not have local infrastructure running:

```bash
poetry run pytest tests/unit/ --tb=short -q
```

## Integration Tests

Integration tests run Alembic migrations and use real MySQL and Redis services.
For a local Docker Compose setup, expose the services on localhost and pass the
Redis password from `.env`:

```bash
docker compose up -d db redis
DB_HOST=127.0.0.1 REDIS_HOST=127.0.0.1 REDIS_PASS=yourstrongpass \
  poetry run pytest tests/integration/ --tb=short -q
```

In GitHub Actions the services are started by the workflow and `REDIS_PASS` is
empty, matching the CI Redis container.

To force local integration runs to fail instead of skip when MySQL or Redis is
missing, set `REQUIRE_INTEGRATION_SERVICES=1`:

```bash
REQUIRE_INTEGRATION_SERVICES=1 poetry run pytest tests/integration/ --tb=short -q
```

## Full Suite

With MySQL and Redis available:

```bash
poetry run pytest --tb=short -q
```

If the services are not available in a local run, integration tests are skipped
with a short message. In CI, or when `REQUIRE_INTEGRATION_SERVICES=1` is set,
missing services fail the run.

## Coverage Gate

CI measures combined coverage for `app/` across unit and integration tests and
fails below 70%. Run the same gate locally when MySQL and Redis are available:

```bash
poetry run coverage erase
poetry run pytest tests/unit/ --cov=app --cov-report= --cov-fail-under=0 --tb=short -q
REQUIRE_INTEGRATION_SERVICES=1 poetry run pytest tests/integration/ \
  --cov=app --cov-append --cov-report= --cov-fail-under=0 --tb=short -q
poetry run coverage report
poetry run coverage xml
```

For a fast local check without infrastructure, run only unit tests; that command
does not enforce the repository-wide coverage threshold.
