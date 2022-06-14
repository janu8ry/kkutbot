FROM python:3.9.13-bullseye AS builder

WORKDIR /kkutbot

COPY pyproject.toml poetry.lock ./

RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-dev


FROM python:3.9.13-slim-bullseye

WORKDIR /kkutbot

COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY . .


CMD ["python", "main.py"]