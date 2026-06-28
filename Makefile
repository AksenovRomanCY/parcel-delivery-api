SHELL := /bin/bash

.PHONY: help install up down logs test-unit test-infra test-integration coverage lint docker-build ci-local smoke

help: ## Show available commands.
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "%-18s %s\n", $$1, $$2}'

install: ## Install Python dependencies with development tools.
	poetry install --with dev --no-root

up: ## Build and start the full Docker Compose stack.
	docker compose up -d --build

down: ## Stop Docker Compose services.
	docker compose down

logs: ## Follow application logs.
	docker compose logs -f app

test-unit: ## Run unit tests.
	poetry run pytest tests/unit/ --tb=short -q

test-infra: ## Start MySQL and Redis for integration tests.
	COMPOSE_ENV_FILE=.env.test docker compose --env-file .env.test up -d db redis

test-integration: ## Run integration tests against local MySQL and Redis.
	set -a; source .env.test; set +a; \
	REQUIRE_INTEGRATION_SERVICES=1 poetry run pytest tests/integration/ --tb=short -q

coverage: ## Run CI-like combined coverage over unit and integration tests.
	poetry run coverage erase
	poetry run pytest tests/unit/ --cov=app --cov-report= --cov-fail-under=0 --tb=short -q
	set -a; source .env.test; set +a; \
	REQUIRE_INTEGRATION_SERVICES=1 poetry run pytest tests/integration/ \
	  --cov=app --cov-append --cov-report= --cov-fail-under=0 --tb=short -q
	poetry run coverage report
	poetry run coverage xml

lint: ## Run format, lint, type, and security checks.
	poetry run ruff format --check .
	poetry run ruff check .
	poetry run mypy app tests
	poetry run bandit -c pyproject.toml -r app

docker-build: ## Build the application Docker image.
	docker build -t parcel-delivery-api:local-check .

ci-local: lint test-infra ## Run the local equivalent of CI checks.
	set -a; source .env.test; set +a; poetry run alembic upgrade head
	$(MAKE) coverage
	$(MAKE) docker-build

smoke: ## Run end-to-end smoke checks against a running app.
	scripts/smoke_test.sh

