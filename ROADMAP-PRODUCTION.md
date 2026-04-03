# ROADMAP: Фазы 3-4 — Security & Observability

> Продолжение [ROADMAP.md](ROADMAP.md) (фазы 1-2).
> Фазы 3-4 делаются после завершения фаз 1-2.

---

## Фаза 3 — Security

> Пункты 3.1 и 3.3 можно делать **параллельно**. 3.2 — после 3.1.
> 3.4 — независимый, параллельно с любым.

### 3.1 Rate Limiting

**Проблема:** API полностью открыт. Любой может генерировать бесконечные сессии
и создавать посылки без ограничений. DDoS, спам, исчерпание ресурсов БД.

**Решение:** Библиотека `slowapi` (обёртка над `limits`, интеграция с FastAPI).

**A) Установить:**

```toml
# pyproject.toml
dependencies = [
    # ...existing...
    "slowapi (>=0.1.9,<1.0.0)",
]
```

**B) Настроить лимитер `app/core/rate_limit.py`:**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri="redis://:{password}@{host}:{port}/1",  # отдельная Redis DB
)
```

**C) Подключить в `app/main.py`:**

```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**D) Применить к эндпоинтам:**

```python
from app.core.rate_limit import limiter

@router.post("/parcels", status_code=201)
@limiter.limit("20/minute")
async def create_parcel(request: Request, ...):
    ...

@router.post("/tasks/recalc-delivery")
@limiter.limit("5/minute")
async def trigger_recalc(request: Request):
    ...
```

**E) Рекомендуемые лимиты:**

| Эндпоинт | Лимит | Обоснование |
|----------|-------|------------|
| `POST /parcels` | 20/min | Защита от спама |
| `GET /parcels` | 60/min | Нормальное использование |
| `GET /parcels/{id}` | 60/min | Нормальное использование |
| `GET /parcel-types` | 100/min | Кешируется, легковесный |
| `POST /tasks/recalc-delivery` | 5/min | Тяжёлая операция |

**F) Добавить переменные в `app/core/settings.py`:**

```python
RATE_LIMIT_DEFAULT: str = "100/minute"
RATE_LIMIT_CREATE: str = "20/minute"
RATE_LIMIT_RECALC: str = "5/minute"
```

---

### 3.2 JWT / OAuth2 аутентификация

**Проблема:** Анонимные UUID-сессии — не аутентификация. Любой, знающий
чужой `X-Session-Id`, получит доступ к чужим посылкам.

**Решение:** JWT-токены через `python-jose` + `passlib`. Сессионный UUID
становится `sub` claim в JWT.

> Это самый крупный пункт. Рекомендуется выделить в отдельную ветку.

**A) Зависимости:**

```toml
"python-jose[cryptography] (>=3.3.0,<4.0.0)",
"passlib[bcrypt] (>=1.7.4,<2.0.0)",
```

**B) Настройки `app/core/settings.py`:**

```python
JWT_SECRET_KEY: str = "change-me-in-production"
JWT_ALGORITHM: str = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MIN: int = 30
```

**C) Модуль `app/core/security.py`:**

```python
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.core.settings import settings

def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MIN
    )
    return jwt.encode(
        {"sub": subject, "exp": expire},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload.get("sub")
    except JWTError:
        return None
```

**D) Dependency `app/api/deps.py`:**

```python
from fastapi import Depends, Header
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedError

async def get_current_user(authorization: str = Header(...)) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError("Invalid authorization header")
    subject = decode_token(token)
    if not subject:
        raise UnauthorizedError("Invalid or expired token")
    return subject
```

**E) Миграция:**
1. Добавить модель `User` (id, email, hashed_password, created_at)
2. Alembic-миграция
3. Эндпоинты `POST /auth/register`, `POST /auth/login`
4. Привязать `Parcel.session_id` → `Parcel.user_id` (FK)
5. Обновить middleware — JWT вместо `X-Session-Id`

**F) Обратная совместимость:** Поддерживать оба режима (анонимный + JWT) на
переходный период через feature flag `AUTH_REQUIRED: bool = False` в Settings.

---

### 3.3 CHECK constraints на уровне БД

**Проблема:** Ограничения (вес > 0, стоимость >= 0) — только в Python. БД принимает
любые значения напрямую.

**A) Alembic-миграция:**

```python
from alembic import op

def upgrade():
    op.create_check_constraint(
        "ck_parcel_weight_positive",
        "parcel",
        "weight_kg > 0",
    )
    op.create_check_constraint(
        "ck_parcel_value_non_negative",
        "parcel",
        "declared_value_usd >= 0",
    )
    op.create_check_constraint(
        "ck_parcel_cost_non_negative",
        "parcel",
        "delivery_cost_rub >= 0 OR delivery_cost_rub IS NULL",
    )

def downgrade():
    op.drop_constraint("ck_parcel_weight_positive", "parcel", type_="check")
    op.drop_constraint("ck_parcel_value_non_negative", "parcel", type_="check")
    op.drop_constraint("ck_parcel_cost_non_negative", "parcel", type_="check")
```

**B) Обновить ORM-модель** — добавить `CheckConstraint` в `__table_args__`:

```python
from sqlalchemy import CheckConstraint

class Parcel(Base):
    __tablename__ = "parcel"
    __table_args__ = (
        CheckConstraint("weight_kg > 0", name="ck_parcel_weight_positive"),
        CheckConstraint("declared_value_usd >= 0", name="ck_parcel_value_non_negative"),
        CheckConstraint(
            "delivery_cost_rub >= 0 OR delivery_cost_rub IS NULL",
            name="ck_parcel_cost_non_negative",
        ),
    )
```

> MySQL 8.0.16+ поддерживает CHECK constraints (ранее игнорировал).

---

### 3.4 Graceful shutdown для Redis

**Проблема:** Redis-клиент — singleton без явного закрытия. При остановке
приложения соединения утекают.

**A) Добавить функцию закрытия в `app/redis_client/client.py`:**

```python
async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
```

**B) Использовать lifespan в `app/main.py`:**

```python
from contextlib import asynccontextmanager
from app.redis_client import close_redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()

app = FastAPI(
    title="Parcel-Delivery-API",
    lifespan=lifespan,
    # ...
)
```

**C) Аналогично для scheduler** в `app/scheduler_main.py` — вызывать `close_redis()`
в signal handler при SIGTERM/SIGINT.

---

## Фаза 4 — Observability & Infrastructure

> Все пункты фазы 4 **независимы** — можно делать параллельно.

### 4.1 OpenTelemetry / Prometheus метрики

**Проблема:** Нет метрик. Невозможно отследить латентность, частоту ошибок,
скорость пересчёта стоимости.

**A) Зависимости:**

```toml
"prometheus-fastapi-instrumentator (>=7.0.0,<8.0.0)",
# Или полный OpenTelemetry стек:
# "opentelemetry-api",
# "opentelemetry-sdk",
# "opentelemetry-instrumentation-fastapi",
# "opentelemetry-exporter-prometheus",
```

**B) Быстрый старт с Prometheus (рекомендуется для начала):**

```python
# app/main.py
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_respect_env_var=True,
    env_var_name="ENABLE_METRICS",
)

app = FastAPI(...)
instrumentator.instrument(app).expose(app, endpoint="/metrics")
```

**C) Кастомные метрики `app/core/metrics.py`:**

```python
from prometheus_client import Counter, Histogram

PARCELS_CREATED = Counter(
    "parcels_created_total", "Total parcels created",
    ["parcel_type"],
)

DELIVERY_RECALC_DURATION = Histogram(
    "delivery_recalc_duration_seconds",
    "Time spent on delivery cost recalculation",
)

DELIVERY_RECALC_PARCELS = Counter(
    "delivery_recalc_parcels_total",
    "Total parcels recalculated",
)
```

**D) Docker Compose — добавить Prometheus:**

```yaml
prometheus:
  image: prom/prometheus:latest
  ports: ["9090:9090"]
  volumes:
    - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml

# prometheus.yml:
scrape_configs:
  - job_name: "parcel-api"
    static_configs:
      - targets: ["fastapi_app:8000"]
```

**E) Grafana (опционально):**

```yaml
grafana:
  image: grafana/grafana:latest
  ports: ["3000:3000"]
  depends_on: [prometheus]
```

---

### 4.2 Sentry для отслеживания ошибок

**Проблема:** Ошибки видны только в stdout логах контейнера. Нет группировки,
трейсов, алертов.

**A) Зависимость:**

```toml
"sentry-sdk[fastapi] (>=2.0.0,<3.0.0)",
```

**B) Настройки:**

```python
# app/core/settings.py
SENTRY_DSN: str = ""  # пусто = Sentry отключен
SENTRY_TRACES_SAMPLE_RATE: float = 0.1
```

**C) Инициализация в `app/main.py`:**

```python
import sentry_sdk
from app.core.settings import settings

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        environment=settings.ENVIRONMENT,
        release=app.version,
    )
```

**D) `.env.example`:**

```ini
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.1
```

> Sentry бесплатен для open-source и малых команд (до 5k ошибок/мес).

---

### 4.3 Рассмотреть PostgreSQL (опционально)

**Контекст:** MySQL работает, но PostgreSQL лучше интегрирован в Python-экосистему.

**Аргументы за миграцию:**

| Критерий | MySQL + aiomysql | PostgreSQL + asyncpg |
|----------|-----------------|---------------------|
| Async-производительность | Средняя | Высокая (asyncpg на C) |
| Типы данных | Базовые | JSONB, ARRAY, ENUM, Range |
| Полнотекстовый поиск | Limited | Встроенный |
| Поддержка в SQLAlchemy | Хорошая | Лучшая |
| Поддержка в Alembic | Хорошая | Лучшая |
| Docker images | Тяжелее | Легче (alpine) |

**Если мигрировать — план:**

1. Добавить `asyncpg` и `psycopg2-binary` в зависимости
2. Изменить `DB_PROTOCOL` на `postgresql+asyncpg`
3. Заменить `pymysql` на `psycopg2-binary`
4. Обновить `docker-compose.yml`: `postgres:16-alpine` вместо `mysql:8.4`
5. Перегенерировать Alembic-миграции
6. Заменить `INSERT...ON DUPLICATE KEY` на `INSERT...ON CONFLICT` в seed-миграции
7. Обновить MySQL-специфичный `docker/mysql/` конфиг

**Если НЕ мигрировать:**

Обновить MySQL 8.0 → 8.4 (LTS). Обратно совместим, просто поменять тег в
`docker-compose.yml`:

```yaml
db:
  image: mysql:8.4
```

---

### 4.4 Рассмотреть Celery / arq (опционально)

**Контекст:** APScheduler 3.x — хороший выбор для текущего масштаба. Но если
потребуется распределённое выполнение задач (несколько воркеров, приоритеты,
retry, мониторинг), стоит рассмотреть альтернативы.

| Критерий | APScheduler 3.x | Celery + Redis | arq |
|----------|----------------|---------------|-----|
| Сложность | Низкая | Высокая | Низкая |
| Distributed | Нет | Да | Да |
| Async native | Частично | Нет (gevent/eventlet) | Да |
| Dashboard | Нет | Flower | arq-dashboard |
| Retry/Backoff | Нет | Да | Да |
| Зрелость | Высокая | Высокая | Средняя |

**Рекомендация:** Оставить APScheduler, пока не появится потребность в distributed
задачах. Если появится — **arq** (async-native, Redis-based) предпочтительнее
Celery для async-стека.

---

## Порядок параллельной работы

```
                    ┌─ 1.1 DECIMAL ─────────────┐
                    │                            │
Фаза 1 ─┤├─ 1.2 Dependencies ─────────┤├─ 1.4 mypy ─── 1.5 Config ──┐
                    │                            │                      │
                    ├─ 1.3 Ruff ────────────────┘                      │
                    └─ 1.6 Poetry/pyproject ────┘                      │
                                                                       │
         ┌─ 2.1 CI/CD ─────────────────────────────────────────────────┤
         │                                                              │
Фаза 2 ─┤├─ 2.3 Multi-stage Docker ───────────────────────────────────┤
         │                                                              │
         ├─ 2.4 Redis healthcheck ─────────────────────────────────────┤
         │                                                              │
         └─ 2.2 Integration tests (после 1.1) ────────────────────────┤
                                                                       │
         ┌─ 3.1 Rate limiting ──── 3.2 JWT auth ──────────────────────┤
         │                                                              │
Фаза 3 ─┤├─ 3.3 CHECK constraints ────────────────────────────────────┤
         │                                                              │
         └─ 3.4 Graceful shutdown ─────────────────────────────────────┤
                                                                       │
         ┌─ 4.1 Prometheus / metrics ──────────────────────────────────┤
         │                                                              │
Фаза 4 ─┤├─ 4.2 Sentry ───────────────────────────────────────────────┤
         │                                                              │
         └─ 4.3 PostgreSQL / MySQL 8.4 upgrade ────────────────────────┘
```

---

## Чек-лист

### Фаза 3 — Security
- [ ] 3.1 Rate limiting (slowapi) + конфигурация лимитов
- [ ] 3.2 JWT аутентификация: модель User, эндпоинты auth, миграция session_id → user_id
- [ ] 3.3 CHECK constraints в MySQL (weight > 0, value >= 0)
- [ ] 3.4 Graceful shutdown Redis: `aclose()` в lifespan + scheduler signal handler

### Фаза 4 — Observability & Infrastructure
- [ ] 4.1 Prometheus метрики: instrumentator + кастомные counters/histograms
- [ ] 4.2 Sentry: SDK + конфигурация через env
- [ ] 4.3 Миграция на PostgreSQL или обновление MySQL 8.0 → 8.4

---

## Итого: полный список пунктов

| # | Пункт | Фаза | Приоритет | Сложность |
|---|-------|------|-----------|-----------|
| 1.1 | FLOAT → DECIMAL | 1 | Критический | Средняя |
| 1.2 | Обновление зависимостей | 1 | Критический | Низкая |
| 1.3 | black + isort → Ruff | 1 | Высокий | Низкая |
| 1.4 | Добавить mypy | 1 | Высокий | Средняя |
| 1.5 | Вынести константы в конфиг | 1 | Средний | Низкая |
| 1.6 | Исправить Poetry / pyproject.toml | 1 | Средний | Низкая |
| 2.1 | GitHub Actions CI/CD | 2 | Критический | Средняя |
| 2.2 | Интеграционные тесты | 2 | Высокий | Средняя |
| 2.3 | Multi-stage Docker | 2 | Средний | Низкая |
| 2.4 | Redis healthcheck | 2 | Средний | Низкая |
| 3.1 | Rate limiting | 3 | Высокий | Низкая |
| 3.2 | JWT аутентификация | 3 | Высокий | Высокая |
| 3.3 | CHECK constraints | 3 | Средний | Низкая |
| 3.4 | Graceful shutdown Redis | 3 | Средний | Низкая |
| 4.1 | Prometheus метрики | 4 | Средний | Средняя |
| 4.2 | Sentry | 4 | Средний | Низкая |
| 4.3 | PostgreSQL / MySQL 8.4 | 4 | Низкий | Высокая |
