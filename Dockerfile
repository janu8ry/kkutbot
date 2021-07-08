FROM python:3.9.5-slim-buster AS builder

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.9.5-slim-buster

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY . .

RUN mkdir backup && \
    mkdir logs


CMD ["python", "main.py"]
