# ── builder ──
FROM python:3.13-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    pip install --no-cache-dir "poetry>=2.1,<3.0" && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false && \
    poetry export -f requirements.txt --without-hashes -o requirements.txt && \
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
