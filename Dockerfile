# BASE STAGE ========================================================

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS base

# The virtualenv lives outside /app so the dev bind-mount does not hide it
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./

# DEVELOPMENT STAGE ========================================================

FROM base AS dev

# All dependencies, including the dev group (ruff)
RUN uv sync --frozen --no-install-project

COPY . .

EXPOSE 3000

# Apply pending migrations, then start with hot reload
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --reload --host 0.0.0.0 --port 3000"]

# PRODUCTION DEPENDENCIES ========================================================

FROM base AS deps-prod

# Only runtime dependencies (no dev group)
RUN uv sync --frozen --no-install-project --no-dev

# PRODUCTION STAGE ========================================================

FROM python:3.13-slim-bookworm AS prod

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=deps-prod /opt/venv /opt/venv
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY public ./public

# Run as an unprivileged user
RUN useradd --system --no-create-home app
USER app

EXPOSE 3000

# Apply pending migrations, then start the app
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 3000"]
