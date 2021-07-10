FROM python:3.9.6-slim-buster

WORKDIR /kkutbot

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN apt-get update && \
    apt-get install -y wget && \
    wget https://fastdl.mongodb.org/tools/db/mongodb-database-tools-debian92-x86_64-100.3.1.deb && \
    apt-get install -y ./mongodb-database-tools-*.deb && \
    rm -f mongodb-database-tools-*.deb && \
    apt-get clean all && \
    mkdir backup && \
    mkdir logs


CMD ["python", "main.py"]
