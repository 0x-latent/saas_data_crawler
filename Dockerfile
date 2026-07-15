FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements-api.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 180 --retries 10 -r requirements-api.txt

COPY . .

FROM base AS api

CMD ["uvicorn", "saas_crawler.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS browser-worker

ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 180 --retries 10 playwright==1.61.0

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get -o Acquire::Retries=10 -o Acquire::http::Timeout=120 update \
    && apt-get -o Acquire::Retries=10 -o Acquire::http::Timeout=120 install -y --no-install-recommends chromium ca-certificates

CMD ["python", "-m", "saas_crawler.tasks.worker"]
