FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    openjdk-25-jdk \
    gcc \
    build-essential \
    bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia il jar, lo script bash e gli eventuali file di test
COPY . /app

# Rende eseguibile lo script
RUN chmod +x MyFun2C.sh

# Il comando di default per i test in locale
CMD ["./MyFun2C.sh", "test_sorgente.txt", "test_input.txt"]