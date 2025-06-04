FROM python:3.13.3-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM python:3.13.3-slim-bookworm

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY . .

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "/app/main.py"]