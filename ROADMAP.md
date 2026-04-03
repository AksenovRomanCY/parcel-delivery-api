# ROADMAP: Фазы 1-2 — Foundation & CI/CD

> Дорожная карта развития. Фазы 1-2 здесь, фазы 3-4 в [ROADMAP-PRODUCTION.md](ROADMAP-PRODUCTION.md).

## Обзор фаз

| Фаза | Название | Суть | Зависит от |
|------|---------|------|-----------|
| **1** | Foundation | Целостность данных, зависимости, линтинг, типизация | — |
| **2** | CI/CD & Testing | GitHub Actions, интеграционные тесты, Docker | Фаза 1 (частично) |
| **3** | Security | Rate limiting, JWT, DB constraints, graceful shutdown | Фаза 2 |
| **4** | Observability | Метрики, Sentry, обновление инфраструктуры | Фаза 3 |

---

## Фаза 1 — Foundation

> Пункты 1.1–1.3 можно делать **параллельно**. 1.4–1.5 — после них.

### 1.1 FLOAT → DECIMAL для денежных полей

**Проблема:** `Float` теряет точность: `0.1 + 0.2 = 0.30000000000000004`.

**Шаги:**

**A) Модель `app/models/parcel.py`** — заменить `Float` на `Numeric`:

```python
from sqlalchemy import Numeric
from decimal import Decimal

weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
declared_value_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
delivery_cost_rub: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
```

**B) Pydantic-схемы `app/schemas/parcel.py`** — `float` → `Decimal`:

```python
from decimal import Decimal
from pydantic import condecimal

class ParcelCreate(BaseModel):
    weight_kg: condecimal(gt=Decimal("0"), max_digits=10, decimal_places=3)
    declared_value_usd: condecimal(ge=Decimal("0"), max_digits=12, decimal_places=2)
```

**C) Формула `app/tasks/delivery.py`** — убрать `float()` обёртки:

```python
async def _formula(weight: Decimal, declared: Decimal, rate: Decimal) -> Decimal:
    return (weight * Decimal("0.5") + declared * Decimal("0.01")) * rate

# В recalc_delivery_costs — убрать float() и Decimal() конверсии:
parcel.delivery_cost_rub = await _formula(
    parcel.weight_kg, parcel.declared_value_usd, rate
)
```

**D) Alembic-миграция:**

```bash
alembic revision --autogenerate -m "float_to_decimal"
```

Проверить, что сгенерирован `alter_column` с `type_=sa.Numeric(...)`.

---

### 1.2 Обновление зависимостей

> Параллельно с 1.1 и 1.3. Полная матрица версий — в конце файла.

**A) Ослабить version constraints в `pyproject.toml`:**

```toml
dependencies = [
    "fastapi (>=0.115.12,<1.0.0)",         # было <0.116.0
    "uvicorn[standard] (>=0.34.2,<1.0.0)",  # было <0.35.0
    "sqlalchemy[asyncio] (>=2.0.41,<3.0.0)",
    "aiomysql (>=0.2.0,<1.0.0)",            # было <0.3.0
    "alembic (>=1.16.1,<2.0.0)",
    "pydantic (>=2.11.5,<3.0.0)",
    "httpx (>=0.28.1,<1.0.0)",              # было <0.29.0
    "pydantic-settings (>=2.9.1,<3.0.0)",
    "pymysql (>=1.1.1,<2.0.0)",
    "tenacity (>=9.1.2,<10.0.0)",
    "apscheduler (>=3.11.0,<4.0.0)",
    "redis (>=5.0.0,<8.0.0)",              # было >=4.5,<5.0 — МАЖОРНЫЙ АПДЕЙТ
]
```

**B) Redis клиент 4.x → 5.x+** — основные breaking changes:
- `decode_responses=False` по умолчанию (проект уже передаёт `True` — ОК)
- Удалены deprecated аргументы
- Импорт `redis.asyncio.Redis` не изменился

Проверить: `app/redis_client/client.py`, `app/tasks/delivery.py` (`.set()` с `ex`/`nx`).

**C) Docker-образы** в `docker-compose.yml`:

```yaml
db:
  image: mysql:8.4  # было: 8.0 — текущий LTS

# redis:7-alpine — оставить (стабильный)
```

**D) Команды обновления:**

```bash
poetry lock && poetry install
pytest
docker compose build --no-cache && docker compose up -d
curl http://localhost:8000/health
```

---

### 1.3 Замена black + isort → Ruff

**Проблема:** 2 отдельных инструмента. Ruff заменяет оба + flake8 + pyupgrade,
в 10-100x быстрее (Rust). Стандарт индустрии с 2024.

**A) `pyproject.toml`** — удалить `[tool.black]`, `[tool.isort]`, заменить зависимости:

```toml
[tool.poetry.group.dev.dependencies]
ruff = ">=0.11.0"
pre-commit = "^4.2.0"
pytest = "^8.3.5"
pytest-asyncio = "^1.0.0"
# black и isort — УДАЛИТЬ

[tool.ruff]
target-version = "py313"
line-length = 88

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "B", "SIM", "N"]

[tool.ruff.lint.isort]
known-first-party = ["app"]
```

**B) `.pre-commit-config.yaml`:**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.11.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-ast
      - id: check-yaml
```

**C) Первый прогон:**

```bash
poetry install
ruff format .
ruff check --fix .
pre-commit autoupdate && pre-commit run --all-files
```

---

### 1.4 Статический анализ типов (mypy)

> После 1.1 (Decimal) и 1.3 (Ruff) — они меняют типы и импорты.

**A) Установить и настроить** в `pyproject.toml`:

```toml
[tool.poetry.group.dev.dependencies]
mypy = "^1.15.0"

[tool.mypy]
python_version = "3.13"
strict = true
plugins = ["pydantic.mypy", "sqlalchemy.ext.mypy.plugin"]

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

**B) Добавить в `.pre-commit-config.yaml`:**

```yaml
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.15.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, "sqlalchemy[mypy]"]
```

**C) Постепенное внедрение:** если strict выдаёт много ошибок — начать с
`strict = false` + `disallow_untyped_defs = true`, включать правила поэтапно.

---

### 1.5 Вынести захардкоженные константы в конфигурацию

**Проблема:** Формула (`0.5`, `0.01`), batch size (`500`), TTL (`60`, `600`) —
в коде. Менять = деплоить.

**A) Расширить `app/core/settings.py`:**

```python
from decimal import Decimal

class Settings(BaseSettings):
    # ... existing ...
    DELIVERY_WEIGHT_COEFF: Decimal = Decimal("0.5")
    DELIVERY_VALUE_COEFF: Decimal = Decimal("0.01")
    DELIVERY_BATCH_SIZE: int = 500
    DELIVERY_JOB_INTERVAL_MIN: int = 5
    DELIVERY_LOCK_TTL: int = 330
    CACHE_TTL_DEFAULT: int = 60
    CACHE_TTL_RATE: int = 600
```

**B) Обновить `app/tasks/delivery.py`** — использовать `settings.*` вместо магических чисел.

**C) Обновить `app/tasks/scheduler.py`** — `minute="*/5"` → `minutes=settings.DELIVERY_JOB_INTERVAL_MIN`.

**D) Обновить `.env.example`** — добавить новые переменные с дефолтными значениями.

---

### 1.6 Исправление конфигурации Poetry / pyproject.toml

> Параллельно с 1.1–1.3. Логично совместить с 1.2 (зависимости) и 1.3 (Ruff)
> в одном коммите, т.к. все правки в `pyproject.toml`.

**Проблема:** `poetry check` проходит, но конфигурация содержит несогласованности
и нарушения best practices, которые затруднят обновления и путают новых разработчиков.

**A) Убрать скобки из version specs в `[project].dependencies`:**

Сейчас используется Poetry-стиль со скобками, а `[tool.poetry.group.dev]` — `^`-нотацию.
Секция `[project]` — PEP 621 стандарт, зависимости должны быть в PEP 508 (без скобок):

```toml
# Было (Poetry-стиль):
"fastapi (>=0.115.12,<0.116.0)"

# Стало (PEP 508):
"fastapi>=0.115.12,<0.116.0"
```

Применить ко **всем** строкам в `[project].dependencies`.

**B) Перенести pytest-конфиг из `tests/pytest.ini` в `pyproject.toml`:**

Удалить файл `tests/pytest.ini` и добавить в `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-ra -q"
```

Один файл конфигурации вместо разбросанных — проще поддерживать.

**C) Заполнить пустое описание проекта:**

```toml
[project]
description = "REST API for parcel registration, tracking and delivery cost calculation"
```

**D) Итоговый вид `pyproject.toml` после фазы 1 (1.2 + 1.3 + 1.6):**

```toml
[project]
name = "parcel-delivery-api"
version = "0.1.0"
description = "REST API for parcel registration, tracking and delivery cost calculation"
authors = [
    {name = "Aksenov Roman", email = "aksenov.nsk.r.a@gmail.com"}
]
readme = "README.md"
requires-python = ">=3.13,<4.0"
dependencies = [
    "fastapi>=0.115.12,<1.0.0",
    "uvicorn[standard]>=0.34.2,<1.0.0",
    "sqlalchemy[asyncio]>=2.0.41,<3.0.0",
    "aiomysql>=0.2.0,<1.0.0",
    "alembic>=1.16.1,<2.0.0",
    "pydantic>=2.11.5,<3.0.0",
    "httpx>=0.28.1,<1.0.0",
    "pydantic-settings>=2.9.1,<3.0.0",
    "pymysql>=1.1.1,<2.0.0",
    "tenacity>=9.1.2,<10.0.0",
    "apscheduler>=3.11.0,<4.0.0",
    "redis>=5.0.0,<8.0.0",
]

[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry.group.dev.dependencies]
ruff = ">=0.11.0"
mypy = "^1.15.0"
pre-commit = "^4.2.0"
pytest = "^8.3.5"
pytest-asyncio = "^1.0.0"

[tool.ruff]
target-version = "py313"
line-length = 88

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "B", "SIM", "N"]

[tool.ruff.lint.isort]
known-first-party = ["app"]

[tool.mypy]
python_version = "3.13"
strict = true
plugins = ["pydantic.mypy", "sqlalchemy.ext.mypy.plugin"]

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-ra -q"
```

**E) Удалить `tests/pytest.ini`** после переноса конфига.

---

## Фаза 2 — CI/CD & Testing

> 2.1 и 2.3 можно делать **параллельно** с фазой 1. 2.2 — после 1.1 (Decimal).

### 2.1 GitHub Actions CI/CD

**Проблема:** Тесты, линтинг, сборка — всё вручную. Нет автоматизации.

**A) Создать `.github/workflows/ci.yml`:**

```yaml
name: CI
on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13" }
      - run: pip install poetry && poetry install --with dev
      - run: ruff format --check .
      - run: ruff check .
      - run: mypy app/

  test:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.4
        env: { MYSQL_ROOT_PASSWORD: root, MYSQL_DATABASE: delivery_test }
        ports: ["3306:3306"]
        options: --health-cmd="mysqladmin ping" --health-interval=5s --health-retries=10
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
        options: --health-cmd="redis-cli ping" --health-interval=5s --health-retries=5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13" }
      - run: pip install poetry && poetry install --with dev
      - run: pytest --tb=short -q
        env:
          DB_HOST: 127.0.0.1
          DB_USER: root
          DB_PASSWORD: root
          DB_NAME: delivery_test
          REDIS_HOST: 127.0.0.1
          REDIS_PASS: ""

  docker:
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t parcel-delivery-api:${{ github.sha }} .
```

**B) Защита ветки** — через GitHub UI: Settings → Branches → Branch protection →
require `lint` + `test` checks.

---

### 2.2 Интеграционные и API-тесты

**Проблема:** Только unit-тесты с моками. Нет проверки реального API.

**A) Структура:**

```
tests/
├── unit/            # существующие
├── integration/     # НОВОЕ
│   ├── conftest.py  # фикстуры с реальной БД
│   ├── test_parcel_api.py
│   ├── test_parcel_type_api.py
│   └── test_session_middleware.py
└── conftest.py
```

**B) Фикстуры `tests/integration/conftest.py`:**

```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

**C) Минимальный набор тестов:**

- `POST /parcels` — создание, валидация полей, неизвестный parcel_type
- `GET /parcels` — пагинация, фильтрация по сессии
- `GET /parcels/{id}` — своя/чужая сессия (403/404)
- `GET /parcel-types` — список типов, кеширование
- `GET /health` — 200 OK
- Middleware — автогенерация session_id, невалидный UUID

**D) pytest markers** в `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = ["unit", "integration"]
```

---

### 2.3 Multi-stage Docker build

> Параллельно с любым пунктом — не зависит от кода.

**Проблема:** `build-essential` остаётся в финальном образе (+200-300 MB). Poetry
не закреплён.

**Новый `Dockerfile`:**

```dockerfile
# ── builder ──
FROM python:3.13-slim AS builder
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    pip install --no-cache-dir "poetry>=2.1,<3.0"
WORKDIR /build
COPY pyproject.toml poetry.lock* ./
RUN poetry export -f requirements.txt --without-hashes -o requirements.txt && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── runtime ──
FROM python:3.13-slim
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl netcat-openbsd && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
WORKDIR /code
COPY . .
COPY docker/scripts/wait-for-services.sh /usr/local/bin/wait-for-services.sh
RUN chmod +x /usr/local/bin/wait-for-services.sh && \
    sed -i 's/\r$//' /usr/local/bin/wait-for-services.sh
```

---

### 2.4 Redis healthcheck в docker-compose

**Проблема:** Redis без healthcheck, `condition: service_started` не гарантирует готовность.

**Обновить `docker-compose.yml`:**

```yaml
redis:
  # ...existing...
  healthcheck:
    test: ["CMD", "redis-cli", "-a", "${REDIS_PASS}", "ping"]
    interval: 5s
    timeout: 3s
    retries: 5

# В app и scheduler:
depends_on:
  redis:
    condition: service_healthy  # было: service_started
```

---

## Матрица зависимостей

### Основные

| Пакет | Locked | Новое ограничение | Breaking changes |
|-------|--------|------------------|-----------------|
| `fastapi` | 0.115.12 | `<1.0.0` | Pydantic v1 drop (0.128+) |
| `uvicorn` | 0.34.2 | `<1.0.0` | `uvicorn.workers` deprecated |
| `redis` | 4.6.0 | `>=5.0,<8.0` | API cleanup, defaults |
| `aiomysql` | 0.2.0 | `<1.0.0` | Минорные в 0.3.x |
| `httpx` | 0.28.1 | `<1.0.0` | — |
| `sqlalchemy` | 2.0.41 | Без изм. | — |
| `pydantic` | 2.11.5 | Без изм. | — |
| `alembic` | 1.16.1 | Без изм. | — |
| `tenacity` | 9.1.2 | Без изм. | — |
| `apscheduler` | 3.11.0 | Без изм. | 4.x ещё alpha |
| `pydantic-settings` | 2.9.1 | Без изм. | — |

### Dev-зависимости

| Пакет | Действие | Примечание |
|-------|---------|-----------|
| `black` | **Удалить** | Заменён Ruff |
| `isort` | **Удалить** | Заменён Ruff |
| `ruff` | **Добавить** `>=0.11.0` | Форматирование + линтинг |
| `mypy` | **Добавить** `^1.15.0` | Статический анализ |

### Docker-образы

| Образ | Текущий | Целевой | Примечание |
|-------|---------|---------|-----------|
| `python` | 3.13-slim | 3.13-slim | Стабильный |
| `mysql` | 8.0 | **8.4** | Текущий LTS |
| `redis` | 7-alpine | 7-alpine | Стабильный |

---

## Чек-лист

### Фаза 1
- [ ] 1.1 Float → Decimal: модель, схемы, формула, миграция
- [ ] 1.2 Ослабить version constraints в pyproject.toml
- [ ] 1.2 Redis клиент 4.x → 5.x+
- [ ] 1.2 MySQL image 8.0 → 8.4
- [ ] 1.3 black + isort → Ruff
- [ ] 1.4 Добавить mypy
- [ ] 1.5 Вынести константы в Settings
- [ ] 1.6 Исправить pyproject.toml: PEP 508 формат, описание, pytest.ini → pyproject.toml

### Фаза 2
- [ ] 2.1 GitHub Actions CI/CD
- [ ] 2.2 Интеграционные/API тесты
- [ ] 2.3 Multi-stage Dockerfile
- [ ] 2.4 Redis healthcheck в docker-compose

> Продолжение → [ROADMAP-PRODUCTION.md](ROADMAP-PRODUCTION.md)
