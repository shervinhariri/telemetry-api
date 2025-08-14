#!/usr/bin/env python3
"""
Generate PDF documentation for Step 7: Requests Observability
Creates two PDFs:
1) Step 7 document describing the Requests Observability feature
2) Updated Master Project Scope including Step 7
"""

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF
from datetime import datetime
import os

def add_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(20*mm, 10*mm, f"Live Network Threat Telemetry API — Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    canvas.drawRightString(200*mm, 10*mm, f"Page {doc.page}")
    canvas.restoreState()

def create_styles():
    styles = getSampleStyleSheet()
    
    # Add custom styles
    styles.add(ParagraphStyle(
        name="H1", 
        fontSize=18, 
        leading=22, 
        spaceAfter=8, 
        spaceBefore=6, 
        textColor=colors.HexColor("#0ea5e9")
    ))
    styles.add(ParagraphStyle(
        name="H2", 
        fontSize=14, 
        leading=18, 
        spaceAfter=6, 
        spaceBefore=10, 
        textColor=colors.HexColor("#22c55e")
    ))
    
    # Modify existing Code style
    code_style = styles["Code"]
    code_style.backColor = colors.whitesmoke
    code_style.leftIndent = 6
    code_style.rightIndent = 6
    code_style.spaceBefore = 4
    code_style.spaceAfter = 6
    
    return styles

def create_step7_pdf():
    """Create Step 7: Requests Observability PDF"""
    styles = create_styles()
    
    # Create output directory if it doesn't exist
    os.makedirs("docs", exist_ok=True)
    step7_path = "docs/step7_requests_observability.pdf"
    
    doc = SimpleDocTemplate(
        step7_path, 
        pagesize=A4, 
        leftMargin=18*mm, 
        rightMargin=18*mm, 
        topMargin=16*mm, 
        bottomMargin=16*mm
    )
    flow = []

    # Title
    flow.append(Paragraph("Step 7: Requests Observability — Logs, Metrics, and Live Tail", styles["H1"]))
    flow.append(Paragraph("Goal: Add SOC‑grade visibility into API usage: who connected, what endpoint they called, where they came from, and the outcome, with live tail and export.", styles["BodyText"]))
    flow.append(Spacer(1,6))

    # Endpoints section
    flow.append(Paragraph("New/Updated Endpoints", styles["H2"]))
    endpoints = [
        ["GET /v1/admin/requests", "Paginated, filtered view of request audit records (tenant-scoped)."],
        ["GET /v1/admin/requests/summary?window=15m", "Counts for requests, 2xx/4xx/5xx, P95 latency, active clients."],
        ["GET /v1/admin/requests/stream", "Server-Sent Events live tail of request records (filters supported)."],
        ["GET /v1/metrics", "Prometheus metrics include requests_total, request_duration_ms, active_clients (updated)."]
    ]
    tbl = Table(endpoints, colWidths=[70*mm, 90*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
        ("TEXTCOLOR",(0,0),(-1,0),colors.black),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),9),
        ("GRID",(0,0),(-1,-1),0.25,colors.grey),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
    ]))
    flow.append(tbl)
    flow.append(Spacer(1,8))

    # Schemas
    flow.append(Paragraph("Response Schemas", styles["H2"]))
    flow.append(Paragraph("GET /v1/admin/requests — Example item", styles["BodyText"]))
    
    schema_code = """{
  "id": "b0b1...",
  "ts": "2025-08-14T12:45:11Z",
  "tenant_id": "tenant-123",
  "api_key_hash": "hmac:8c9e...",
  "client_ip": "203.0.113.9",
  "user_agent": "curl/8.6.0",
  "method": "POST",
  "path": "/v1/ingest",
  "status": 200,
  "duration_ms": 41,
  "bytes_in": 5241,
  "bytes_out": 238,
  "result": "ok",
  "trace_id": "c6f5a0...",
  "geo_country": "DE",
  "asn": "AS3320"
}"""
    flow.append(Paragraph(schema_code.replace("\n","<br/>").replace("  ","&nbsp;&nbsp;"), styles["Code"]))

    flow.append(Paragraph("GET /v1/admin/requests/summary", styles["BodyText"]))
    summary_code = """{
  "requests": 1234,
  "codes": {"2xx": 1200, "4xx": 20, "5xx": 14},
  "p95_latency_ms": 42,
  "active_clients": 55
}"""
    flow.append(Paragraph(summary_code.replace("\n","<br/>").replace("  ","&nbsp;&nbsp;"), styles["Code"]))

    # Architecture diagram
    flow.append(Spacer(1,6))
    flow.append(Paragraph("High-Level Architecture (Step 7 additions in green)", styles["H2"]))

    d = Drawing(520, 200)
    # Boxes
    d.add(Rect(10, 60, 110, 80, strokeColor=colors.black, fillColor=colors.lightgrey))
    d.add(String(20, 120, "Clients", fontSize=10))
    d.add(String(20, 105, "Ingest / Lookup", fontSize=8))

    d.add(Rect(140, 60, 120, 80, strokeColor=colors.black, fillColor=colors.whitesmoke))
    d.add(String(150, 120, "API Gateway", fontSize=10))
    d.add(String(150, 105, "Auth + Rate Limit", fontSize=8))

    d.add(Rect(280, 60, 120, 80, strokeColor=colors.black, fillColor=colors.whitesmoke))
    d.add(String(290, 120, "Core Services", fontSize=10))
    d.add(String(290, 105, "Enrichment + Risk", fontSize=8))

    d.add(Rect(420, 60, 90, 80, strokeColor=colors.black, fillColor=colors.whitesmoke))
    d.add(String(430, 120, "Outputs", fontSize=10))
    d.add(String(430, 105, "Splunk/Elastic", fontSize=8))

    # New components in green
    d.add(Rect(140, 10, 260, 40, strokeColor=colors.green, fillColor=colors.Color(0.88,1,0.88)))
    d.add(String(150, 30, "Request Audit Logger + /admin/requests + SSE stream", fontSize=9, fillColor=colors.green))

    # Arrows
    d.add(Line(120, 100, 140, 100))
    d.add(Line(260, 100, 280, 100))
    d.add(Line(400, 100, 420, 100))
    flow.append(d)

    # GUI wireframe
    flow.append(PageBreak())
    flow.append(Paragraph("GUI Wireframes — Requests Observability", styles["H1"]))

    wf = Drawing(520, 340)
    # Top cards
    for i, title in enumerate(["Requests (15m)", "2xx / 4xx / 5xx", "P95 Latency (ms)", "Active Clients"]):
        x = 10 + i*125
        wf.add(Rect(x, 290, 115, 40, strokeColor=colors.darkgray, fillColor=colors.whitesmoke))
        wf.add(String(x+6, 313, title, fontSize=8))

    # Tabs
    wf.add(Rect(10, 260, 70, 20, strokeColor=colors.black, fillColor=colors.lightgrey))
    wf.add(String(15, 273, "Dashboard", fontSize=8))
    wf.add(Rect(90, 260, 70, 20, strokeColor=colors.black, fillColor=colors.lightgrey))
    wf.add(String(95, 273, "Requests", fontSize=8))

    # Table area
    wf.add(Rect(10, 20, 500, 230, strokeColor=colors.darkgray, fillColor=colors.whitesmoke))
    headers = ["Time", "IP", "API Key", "Method", "Path", "Status", "Latency", "Bytes", "Result", "Trace"]
    x_positions = [15, 80, 140, 210, 255, 355, 405, 455, 495, 540]
    for i, h in enumerate(headers[:-1]):
        wf.add(String(x_positions[i], 240, h, fontSize=8))
    
    # Sample rows
    for r in range(5):
        y = 220 - r*32
        wf.add(Rect(12, y, 496, 26, strokeColor=colors.lightgrey, fillColor=colors.white))
        wf.add(String(16, y+16, "12:45:11", fontSize=8))
        wf.add(String(80, y+16, "203.0.113.9 🇩🇪", fontSize=8))
        wf.add(String(140, y+16, "abcd****wxyz", fontSize=8))
        wf.add(String(210, y+16, "POST", fontSize=8))
        wf.add(String(255, y+16, "/v1/ingest", fontSize=8))
        
        # Status chip colors
        status_color = colors.green if r < 3 else (colors.orange if r == 3 else colors.red)
        wf.add(Rect(355, y+10, 24, 10, fillColor=status_color, strokeColor=colors.darkgray))
        wf.add(String(358, y+12, "200" if r < 3 else ("429" if r==3 else "500"), fontSize=7, fillColor=colors.white))
        wf.add(String(405, y+16, f"{30+r*10} ms", fontSize=8))
        wf.add(String(455, y+16, "5.1k / 0.2k", fontSize=8))
        wf.add(String(495, y+16, "ok", fontSize=8))

    # Filters
    wf.add(Rect(10, 255, 500, 3, fillColor=colors.darkgray, strokeColor=colors.darkgray))
    wf.add(String(190, 273, "Filters: Status • Endpoint • Method • IP • Time Range | Live Tail ⏵", fontSize=8))

    flow.append(wf)

    # Non-functional requirements
    flow.append(Spacer(1,8))
    flow.append(Paragraph("Non-Functional Requirements", styles["H2"]))
    nfr = [
        ["Performance", "Audit logging must not add >1ms p50 overhead at 1k req/s; async writes; batch flush."],
        ["Security", "Per-tenant scoping; HMAC hashing for API keys; never store request bodies."],
        ["Reliability", "Backpressure on audit writes; drop policy for tail stream if slow consumer."],
        ["Retention", "Automatic purge at 7 days to match MVP data policy."],
    ]
    tbl2 = Table(nfr, colWidths=[35*mm, 125*mm])
    tbl2.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.lightgrey)]))
    flow.append(tbl2)

    doc.build(flow, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    print(f"✅ Created Step 7 PDF: {step7_path}")
    return step7_path

def create_master_scope_pdf():
    """Create Updated Master Project Scope PDF (Steps 1-7)"""
    styles = create_styles()
    
    master_path = "docs/master_project_scope_steps1_7.pdf"
    
    doc2 = SimpleDocTemplate(
        master_path, 
        pagesize=A4, 
        leftMargin=18*mm, 
        rightMargin=18*mm, 
        topMargin=16*mm, 
        bottomMargin=16*mm
    )
    flow2 = []
    
    flow2.append(Paragraph("Live Network Threat Telemetry API — Master Project Scope (Steps 1–7)", styles["H1"]))

    # Steps overview table
    steps = [
        ["1. MVP Scope", "Inputs: NetFlow/IPFIX, Zeek JSON. Enrichments: GeoIP, ASN, TI, Risk. Outputs: Splunk, Elastic, JSON. Retention: 7 days."],
        ["2. Data Models & API Contract", "Base API (/v1), Bearer auth, /ingest, /lookup, /outputs/*, /metrics, schemas and limits."],
        ["3–6. Core Build → Deployment", "Backend implemented, enrichments integrated, outputs wired, Docker image released (0.6.2)."],
        ["7. Requests Observability (NEW)", "Request auditing, summary metrics, live tail, admin endpoints, UI Requests tab, CSV export."]
    ]
    t_master = Table(steps, colWidths=[50*mm, 110*mm])
    t_master.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.lightgrey)]))
    flow2.append(t_master)
    flow2.append(Spacer(1,8))

    flow2.append(Paragraph("Updated Endpoint List (Step 7 additions marked ★)", styles["H2"]))
    ep_all = [
        "/health (GET) — health check",
        "/ingest (POST) — batch upload flows/logs",
        "/lookup (POST) — single enrichment",
        "/outputs/splunk (POST/PUT) — configure Splunk",
        "/outputs/elastic (POST/PUT) — configure Elastic",
        "/alerts/rules (POST/PUT) — webhook alert rule",
        "/metrics (GET) — Prometheus metrics (requests_total, duration, active_clients) ★",
        "/admin/requests (GET) — paginated request audit ★",
        "/admin/requests/summary (GET) — 15m summary ★",
        "/admin/requests/stream (GET) — SSE live tail ★"
    ]
    flow2.append(Paragraph("<br/>".join(ep_all), styles["Code"]))

    flow2.append(Paragraph("Request Audit Record — Canonical Schema", styles["H2"]))
    schema_code = """{
  "id": "b0b1...",
  "ts": "2025-08-14T12:45:11Z",
  "tenant_id": "tenant-123",
  "api_key_hash": "hmac:8c9e...",
  "client_ip": "203.0.113.9",
  "user_agent": "curl/8.6.0",
  "method": "POST",
  "path": "/v1/ingest",
  "status": 200,
  "duration_ms": 41,
  "bytes_in": 5241,
  "bytes_out": 238,
  "result": "ok",
  "trace_id": "c6f5a0...",
  "geo_country": "DE",
  "asn": "AS3320"
}"""
    flow2.append(Paragraph(schema_code.replace("\n","<br/>").replace("  ","&nbsp;&nbsp;"), styles["Code"]))

    flow2.append(Paragraph("Retention Policy", styles["H2"]))
    flow2.append(Paragraph("All audit records follow the existing MVP retention: <b>7 days</b> with daily purge.", styles["BodyText"]))

    flow2.append(Paragraph("UI: Dashboard & Requests Tab Highlights", styles["H2"]))
    gui_list = """
• Dashboard: new mini-cards (Requests 15m, 2xx/4xx/5xx, P95 latency, Active clients)
• Requests Tab: live tail table with filters, CSV export, detail drawer (Geo/ASN, sizes, headers)
• Visuals: small sparkline, stacked status chart, latency histogram, geo map
• UX: compact rows, semantic status chips, masked API keys, copyable Trace ID
"""
    flow2.append(Paragraph(gui_list.replace("\n","<br/>"), styles["BodyText"]))

    # Final notes
    flow2.append(Paragraph("Security & Privacy Notes", styles["H2"]))
    flow2.append(Paragraph("Never store request bodies. Use HMAC-SHA256 to mask API keys. Scope queries to tenant_id. SSE throttled to avoid leaking timing side-channels.", styles["BodyText"]))

    doc2.build(flow2, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    print(f"✅ Created Master Scope PDF: {master_path}")
    return master_path

def main():
    """Generate both PDFs"""
    print("📄 Generating PDF documentation for Step 7: Requests Observability...")
    
    try:
        step7_path = create_step7_pdf()
        master_path = create_master_scope_pdf()
        
        print("\n🎉 PDF Generation Complete!")
        print(f"📋 Step 7 Documentation: {step7_path}")
        print(f"📋 Updated Master Scope: {master_path}")
        print("\n📊 Both PDFs include:")
        print("• New endpoints (/v1/admin/requests, /summary, /stream) with schemas")
        print("• Architecture diagram showing Request Audit path")
        print("• GUI wireframes (dashboard cards + Requests tab live tail)")
        print("• Non-functional requirements and security notes")
        print("• 7-day retention alignment")
        
    except Exception as e:
        print(f"❌ Error generating PDFs: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
