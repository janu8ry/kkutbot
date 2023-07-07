FROM python:3.10.12-bullseye AS builder

WORKDIR /kkutbot

COPY pyproject.toml poetry.lock ./

RUN pip install --no-cache-dir poetry==1.5.1 && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-dev


FROM python:3.10.12-slim-bullseye

WORKDIR /kkutbot

COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY . .

ENV PYTHONUNBUFFERED=0


CMD ["python", "main.py"]