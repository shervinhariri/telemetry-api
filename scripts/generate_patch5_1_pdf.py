#!/usr/bin/env python3
"""
Generate Patch 5.1 PDF Documentation
Creates a concise PDF summarizing the version management and output connectors patch.
"""

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
import os

def generate_patch5_1_pdf():
    doc_path = "docs/patch5_1_version_and_connectors.pdf"
    
    # Ensure docs directory exists
    os.makedirs("docs", exist_ok=True)
    
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    h_style = styles['Heading2']
    body = styles['BodyText']
    body.fontSize = 10
    body.leading = 14
    mono = ParagraphStyle('Mono', parent=body, fontName='Courier', fontSize=9, leading=12)
    
    story = []
    
    story.append(Paragraph("Patch 5.1 – Version Management & Output Connectors", title_style))
    story.append(Spacer(1, 6*mm))
    
    story.append(Paragraph("Scope", h_style))
    scope_items = [
        "Expose /v1/version (service, version, git_sha, image_tag).",
        "Add /v1/updates/check to compare current tag vs latest Docker Hub tag.",
        "Implement Stage 5.1: /v1/outputs/splunk and /v1/outputs/elastic config endpoints.",
        "Add lightweight GUI badge for version + update availability.",
        "Dev-safe update mechanism with admin token authentication."
    ]
    story.append(ListFlowable([ListItem(Paragraph(i, body)) for i in scope_items], bulletType='bullet'))
    story.append(Spacer(1, 4*mm))
    
    story.append(Paragraph("API Endpoints", h_style))
    endpoints = [
        "<b>GET</b> /v1/version → {service, version, git_sha, image, image_tag}",
        "<b>GET</b> /v1/updates/check → {current, latest, update_available}",
        "<b>POST|PUT</b> /v1/outputs/splunk → save Splunk HEC config",
        "<b>GET</b> /v1/outputs/splunk → read config",
        "<b>POST|PUT</b> /v1/outputs/elastic → save Elastic config",
        "<b>GET</b> /v1/outputs/elastic → read config",
        "<b>POST</b> /v1/admin/update → dev-only image pull (requires X-Admin-Token)"
    ]
    story.append(ListFlowable([ListItem(Paragraph(i, body)) for i in endpoints], bulletType='1'))
    story.append(Spacer(1, 4*mm))
    
    story.append(Paragraph("Quick cURL Tests", h_style))
    curl_block = """
# Version
curl -s http://localhost:8080/v1/version

# Check for updates
curl -s http://localhost:8080/v1/updates/check

# Configure Splunk
curl -s -X POST http://localhost:8080/v1/outputs/splunk \\
  -H "Authorization: Bearer TEST_KEY" \\
  -H 'Content-Type: application/json' \\
  -d '{"hec_url":"https://splunk.example:8088/services/collector","token":"***","index":"telemetry","sourcetype":"telemetry:event"}'

# Configure Elastic
curl -s -X POST http://localhost:8080/v1/outputs/elastic \\
  -H "Authorization: Bearer TEST_KEY" \\
  -H 'Content-Type: application/json' \\
  -d '{"urls":["https://es1:9200"],"index_prefix":"telemetry-","bulk_size":1000}'

# Dev-only: pull latest image
curl -s -X POST http://localhost:8080/v1/admin/update \\
  -H "X-Admin-Token: dev-only-token"
"""
    story.append(Paragraph(curl_block.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n","<br/>"), mono))
    story.append(Spacer(1, 4*mm))
    
    story.append(Paragraph("Docker Build & Push (tag v0.5.1)", h_style))
    docker_block = """
export APP_VERSION=v0.5.1
export GIT_SHA=$(git rev-parse --short HEAD)
docker build -t shvin/telemetry-api:$APP_VERSION \\
  --build-arg APP_VERSION=$APP_VERSION \\
  --build-arg GIT_SHA=$GIT_SHA .
docker push shvin/telemetry-api:$APP_VERSION

# Run locally
docker run --rm -p 8080:8080 \\
  -e API_KEYS=TEST_KEY \\
  -e APP_VERSION=$APP_VERSION \\
  -e GIT_SHA=$GIT_SHA \\
  -e ADMIN_TOKEN=dev-only-token \\
  shvin/telemetry-api:$APP_VERSION
"""
    story.append(Paragraph(docker_block.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n","<br/>"), mono))
    story.append(Spacer(1, 4*mm))
    
    story.append(Paragraph("Production Deployment", h_style))
    watchtower_block = """
# docker-compose.yml
services:
  telemetry-api:
    image: shvin/telemetry-api:latest
    environment:
      - API_KEYS=TEST_KEY
      - APP_VERSION=0.5.1
      - UPDATE_CHECK_ENABLED=true
    ports:
      - "8080:8080"
  
  watchtower:
    image: containrrr/watchtower
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --cleanup --interval 60 telemetry-api
"""
    story.append(Paragraph(watchtower_block.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n","<br/>"), mono))
    story.append(Spacer(1, 4*mm))
    
    story.append(Paragraph("Notes", h_style))
    notes = [
        "Public health check /v1/health remains unauthenticated.",
        "Version badge shows green (up-to-date) or amber (update available).",
        "Update checks occur every 60 seconds automatically.",
        "Watchtower provides production auto-updates while GUI shows availability.",
        "Admin update endpoint is dev-only and requires X-Admin-Token header.",
        "Output connector configs are stored in-memory (MVP implementation)."
    ]
    story.append(ListFlowable([ListItem(Paragraph(i, body)) for i in notes], bulletType='bullet'))
    
    doc = SimpleDocTemplate(doc_path, pagesize=A4,
                            leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    doc.build(story)
    
    print(f"PDF generated: {doc_path}")
    return doc_path

if __name__ == "__main__":
    generate_patch5_1_pdf()
