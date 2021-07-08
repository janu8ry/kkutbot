FROM python:3.9.5-slim-buster AS builder

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.9.5-slim-buster

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY . .

RUN apt-get update && \
    apt-get install -y wget && \
    wget https://fastdl.mongodb.org/tools/db/mongodb-database-tools-debian92-x86_64-100.3.1.deb && \
    apt-get install -y ./mongodb-database-tools-*.deb && \
    rm -f mongodb-database-tools-*.deb && \
    mkdir backup && \
    mkdir logs


CMD ["python", "main.py"]
