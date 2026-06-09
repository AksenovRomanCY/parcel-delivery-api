# Running Tests

Test configuration lives in `pyproject.toml` under `[tool.pytest.ini_options]`.
The suite is split into fast unit tests and integration tests that require MySQL
and Redis.

## Test Authoring Standards

Every test must use the AAA structure and mark the sections explicitly:

```python
def test_example() -> None:
    """Describe the behavior, not the implementation."""
    # Arrange
    ...

    # Act
    ...

    # Assert
    ...
```

Use factory fixtures for repeated test data setup instead of duplicating DTO,
ORM model, request, or API payload construction. Keep factories simple pytest
fixtures unless a real need appears for an external factory library.

Use `pytest.mark.parametrize` when multiple cases share the same Arrange/Act/
Assert flow and only the input or expected result changes. Keep meaningfully
different scenarios as separate tests.

Mock external dependencies in unit tests: database sessions, Redis, HTTP
clients, Sentry, and scheduler/task side effects. Integration tests should use
real MySQL and Redis services through the test fixtures.

Integration tests must run against a dedicated test database named
`delivery_test`. Do not run integration tests against the application database
`delivery`, because the fixtures clean mutable tables before each test.
Use `.env.test` for local test infrastructure; it keeps legacy auth explicit for
compatibility checks while the main application defaults to JWT auth. Auth
integration tests also verify refresh-cookie rotation and CSRF-protected logout
flows. `.env` remains the application and Docker runtime configuration.

## Unit Tests

Run the unit suite when you do not have local infrastructure running:

```bash
poetry run pytest tests/unit/ --tb=short -q
```

## Integration Tests

Integration tests run Alembic migrations and use real MySQL and Redis services.
For a local Docker Compose setup, expose the services on localhost and load the
same test values used by local pytest commands:

```bash
COMPOSE_ENV_FILE=.env.test docker compose --env-file .env.test up -d db redis
set -a
source .env.test
set +a
REQUIRE_INTEGRATION_SERVICES=1 poetry run pytest tests/integration/ --tb=short -q
```

`--env-file .env.test` controls Docker Compose variable interpolation, such as
published ports and MySQL database name. `COMPOSE_ENV_FILE=.env.test` controls
the `env_file` mounted into services, so Redis gets the same `REDIS_PASS` that
pytest uses.

In GitHub Actions the services are started by the workflow and `REDIS_PASS` is
empty, matching the CI Redis container.

To force local integration runs to fail instead of skip when MySQL or Redis is
missing, set `REQUIRE_INTEGRATION_SERVICES=1`:

```bash
set -a
source .env.test
set +a
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
fails below 85%. Run the same gate locally when MySQL and Redis are available:

```bash
poetry run coverage erase
poetry run pytest tests/unit/ --cov=app --cov-report= --cov-fail-under=0 --tb=short -q
set -a
source .env.test
set +a
REQUIRE_INTEGRATION_SERVICES=1 poetry run pytest tests/integration/ \
  --cov=app --cov-append --cov-report= --cov-fail-under=0 --tb=short -q
poetry run coverage report
poetry run coverage xml
```

For a fast local check without infrastructure, run only unit tests; that command
does not enforce the repository-wide coverage threshold.
