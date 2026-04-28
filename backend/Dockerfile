FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# --- deps stage ---
FROM base AS deps
COPY pyproject.toml .
RUN pip install -e ".[dev]"

# --- development stage (hot-reload, test tools) ---
FROM deps AS development
COPY . .
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# --- production stage ---
FROM base AS production
COPY pyproject.toml .
RUN pip install -e "."
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
