FROM python:3.11-slim

ARG APP_VERSION=0.8.3
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

EXPOSE 80
# Remove default API key; keys must be provided at runtime via env/secrets
ENV APP_PORT=80

# Default MMDB/CSV mount points (read-only)
ENV GEOIP_DB_CITY=/data/GeoLite2-City.mmdb
ENV GEOIP_DB_ASN=/data/GeoLite2-ASN.mmdb
ENV THREATLIST_CSV=/data/threats.csv

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
