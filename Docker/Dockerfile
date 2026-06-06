FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    openjdk-25-jdk \
    gcc \
    build-essential \
    bash \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Installiamo gli SDK di Azure per Python
RUN pip3 install azure-storage-blob azure-storage-queue azure-cosmos

WORKDIR /app
COPY . /app
RUN chmod +x MyFun2C.sh

CMD ["python3", "-u", "worker.py"]