FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy mapper script
COPY nf2ingest.py .

# Make script executable
RUN chmod +x nf2ingest.py

# Run mapper
CMD ["python3", "nf2ingest.py"]
