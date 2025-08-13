FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app/app

# Copy UI files
COPY ops/stage4/ui /app/ui

EXPOSE 8080
ENV API_KEY=TEST_KEY

# Default MMDB/CSV mount points (read-only)
ENV GEOIP_DB_CITY=/data/GeoLite2-City.mmdb
ENV GEOIP_DB_ASN=/data/GeoLite2-ASN.mmdb
ENV THREATLIST_CSV=/data/threats.csv

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
