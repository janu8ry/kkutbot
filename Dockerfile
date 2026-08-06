FROM python:3.14.6-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /kkutbot

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:3.14.6-slim-bookworm

WORKDIR /kkutbot

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgssapi-krb5-2 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=mongo:7.0.37 /usr/bin/mongodump /usr/bin/mongodump
COPY --from=builder /kkutbot/.venv /kkutbot/.venv
COPY . .

ENV PATH="/kkutbot/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
