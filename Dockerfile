# ---- Stage 1: build goflow2 from source (multi-arch safe) ----
FROM golang:1.22 as build-goflow2
ARG GOFLOW_VERSION=v2.2.3
WORKDIR /src
RUN git clone --depth 1 --branch ${GOFLOW_VERSION} https://github.com/netsampler/goflow2.git .
# Build the main binary
RUN CGO_ENABLED=0 go build -o /out/goflow2 ./cmd/goflow2

# ---- Stage 2: app image (API + mapper + goflow2) ----
FROM python:3.11-slim as app

ARG APP_VERSION=0.8.4
ARG GIT_SHA=dev
ARG IMAGE=shvin/telemetry-api

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=${APP_VERSION} \
    GIT_SHA=${GIT_SHA} \
    IMAGE=${IMAGE} \
    DOCKERHUB_REPO=${IMAGE} \
    DOCKERHUB_TAG=${APP_VERSION}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Mapper dependencies
RUN pip install --no-cache-dir requests orjson

COPY app /app/app

# Copy UI files
COPY ops/ui/ui /app/ui

# Copy OpenAPI spec and docs
COPY openapi.yaml /app/openapi.yaml
COPY docs /app/docs

# Copy tests
COPY tests /app/tests

# Copy alembic files for database migrations
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

# Copy scripts for database seeding
COPY scripts /app/scripts

# Add mapper
COPY ops/mapper/nf2ingest.py /app/mapper/nf2ingest.py

# goflow2 binary from previous stage
COPY --from=build-goflow2 /out/goflow2 /usr/local/bin/goflow2
RUN chmod +x /usr/local/bin/goflow2

# Entrypoint orchestrates goflow2 -> FIFO -> mapper -> API
COPY ops/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose GUI/API on 80 (not 8080)
EXPOSE 80
# NetFlow/IPFIX listener
EXPOSE 2055/udp

# Remove default API key; keys must be provided at runtime via env/secrets
ENV APP_PORT=80

# Default MMDB/CSV mount points (read-only)
ENV GEOIP_DB_CITY=/data/GeoLite2-City.mmdb
ENV GEOIP_DB_ASN=/data/GeoLite2-ASN.mmdb
ENV THREATLIST_CSV=/data/threats.csv

ENTRYPOINT ["/app/entrypoint.sh"]
