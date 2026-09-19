# --- Build stage: install dependencies into a venv ---
FROM python:3.13-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# build-essential is needed for some source distributions; kept in builder only.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

# --- Runtime stage: slim image with only the venv + app code ---
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

RUN groupadd --system app && useradd --system --gid app --home /app app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

# The code imports "backend.app..." (package paths are relative to the project root),
# but the image intentionally flattens the layout to /app. Expose the flattened
# directories under /app/backend via symlinks so both alembic and uvicorn resolve them.
RUN mkdir -p /app/backend \
    && ln -s /app/app /app/backend/app \
    && ln -s /app/alembic /app/backend/alembic

# .env is NOT copied: configuration comes from compose environment variables.
RUN chown -R app:app /app
USER app

EXPOSE 8000

# PORT respects the container/platform override (compose sets PORT=8000).
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/v1/health' % os.environ.get('PORT', '8000'), timeout=5)" >/dev/null 2>&1 || exit 1

# Apply migrations, then serve.
CMD ["./entrypoint.sh"]
