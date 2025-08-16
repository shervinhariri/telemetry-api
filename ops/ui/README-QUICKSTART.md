# Quick Start Guide

This guide will help you get the Telemetry API running quickly with the web dashboard.

## Prerequisites

- Docker and Docker Compose installed
- Git (to clone the repository)

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd telemetry-api
   ```

2. **Navigate to the UI directory**
   ```bash
   cd ops/ui
   ```

3. **Start the services**
   ```bash
   docker-compose up -d
   ```

4. **Access the dashboard**
   - Open your browser and go to: http://localhost
   - The dashboard will show real-time metrics and logs

5. **Test the API**
   ```bash
   # Test with sample data
   curl -X POST http://localhost/v1/ingest \
     -H "Authorization: Bearer TEST_KEY" \
     -H "Content-Type: application/json" \
     --data @../../samples/zeek_conn_small.json
   ```

## Features

- **Real-time Dashboard**: Monitor system metrics, requests, and logs
- **Live Logs**: Stream application logs with filtering
- **API Testing**: Built-in API playground for testing endpoints
- **Request Details**: Click on any request to see detailed information

## Configuration

The API key is set to `TEST_KEY` by default. You can change this by:

1. **Environment Variable**: Set `API_KEY` in your environment
2. **Docker Compose**: Add `API_KEY=your_key` to the environment section
3. **Frontend**: Update the API key in the dashboard UI

## Troubleshooting

- **Port 80 already in use**: Change the port in `docker-compose.yml`
- **Permission errors**: Ensure Docker has proper permissions
- **Dashboard not loading**: Check that the container is running with `docker-compose ps`

## Next Steps

- Add your own data sources
- Configure GeoIP databases
- Set up threat intelligence feeds
- Integrate with Splunk or Elasticsearch
