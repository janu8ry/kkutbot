FROM python:3.14-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /kkutbot

RUN apt-get update && apt-get install -y --no-install-recommends cmake && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:3.14-slim-bookworm

WORKDIR /kkutbot

COPY --from=builder /kkutbot/.venv /kkutbot/.venv
COPY . .

ENV PATH="/kkutbot/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
