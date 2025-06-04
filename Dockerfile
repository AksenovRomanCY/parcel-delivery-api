FROM python:3.13-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        netcat-openbsd && \
    pip install --upgrade pip && \
    pip install poetry && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

COPY . .

COPY docker/scripts/wait-for-services.sh /usr/local/bin/wait-for-services.sh
RUN chmod +x /usr/local/bin/wait-for-services.sh \
    && sed -i 's/\r$//' /usr/local/bin/wait-for-services.sh   # на всякий случай убрать CR
