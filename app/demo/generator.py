"""
Demo Generator for Telemetry API
Generates synthetic NetFlow and Zeek events for demonstration purposes.
"""

import asyncio
import random
import time
import ipaddress
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import logging
from . import DEMO_MODE, DEMO_EPS, DEMO_DURATION_SEC, DEMO_VARIANTS

logger = logging.getLogger(__name__)

# Try to import log_system_event; if missing, define a safe fallback
try:
    from ..logging_config import log_system_event
except Exception:
    def log_system_event(event_type: str, message: str = "", fields: dict = None):
        logger.info(f"log_system_event fallback: {event_type} - {message}", extra={"event_type": event_type, **(fields or {})})

class DemoService:
    """Service for managing demo event generation."""
    
    def __init__(self):
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.start_time: Optional[datetime] = None
        
        # Normalize demo base URL
        raw = os.getenv("DEMO_BASE_URL", "http://localhost")
        # ensure scheme; tests run the API on port 80
        if not urlparse(raw).scheme:
            raw = f"http://{raw.lstrip('/')}"
        self.base_url = raw.rstrip("/")
        self.ingest_path = "/v1/ingest"
        self.ingest_url = urljoin(self.base_url + "/", self.ingest_path.lstrip("/"))
        
        # Internal IP ranges for realistic traffic
        self.internal_ranges = [
            "10.0.0.0/8",
            "172.16.0.0/12", 
            "192.168.0.0/16"
        ]
        
        # External IPs for realistic traffic
        self.external_ips = [
            "8.8.8.8", "8.8.4.4",  # Google DNS
            "1.1.1.1", "1.0.0.1",  # Cloudflare DNS
            "208.67.222.222", "208.67.220.220",  # OpenDNS
            "142.250.190.78",  # Google
            "52.84.123.119",   # AWS
            "104.16.124.96",   # Cloudflare
        ]
        
        # Threat IPs (small percentage for realism)
        self.threat_ips = [
            "45.149.3.1", "45.149.3.2", "45.149.3.3",
            "185.220.101.1", "185.220.101.2",
            "91.92.240.1", "91.92.240.2"
        ]
        
        # Common ports
        self.common_ports = [80, 443, 22, 53, 25, 110, 143, 993, 995, 21, 23, 3389, 1433]
        
    def _generate_internal_ip(self) -> str:
        """Generate a random internal IP address."""
        network = random.choice(self.internal_ranges)
        net = ipaddress.IPv4Network(network)
        return str(random.choice(list(net.hosts())))
    
    def _generate_external_ip(self) -> str:
        """Generate a random external IP address."""
        # 3% chance of threat IP for realism
        if random.random() < 0.03:
            return random.choice(self.threat_ips)
        return random.choice(self.external_ips)
    
    def _generate_netflow_event(self) -> Dict[str, Any]:
        """Generate a synthetic NetFlow event."""
        src_ip = self._generate_internal_ip()
        dst_ip = self._generate_external_ip()
        
        return {
            "ts": int(time.time() * 1000),
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": random.randint(1024, 65535),
            "dst_port": random.choice(self.common_ports),
            "protocol": random.choice(["tcp", "udp"]),
            "bytes": random.randint(64, 50000),
            "packets": random.randint(1, 100),
            "demo": True
        }
    
    def _generate_zeek_event(self) -> Dict[str, Any]:
        """Generate a synthetic Zeek connection event."""
        src_ip = self._generate_internal_ip()
        dst_ip = self._generate_external_ip()
        
        return {
            "ts": int(time.time() * 1000),
            "uid": f"C{random.randint(1000000000, 9999999999)}",
            "id_orig_h": src_ip,
            "id_orig_p": random.randint(1024, 65535),
            "id_resp_h": dst_ip,
            "id_resp_p": random.choice(self.common_ports),
            "proto": random.choice(["tcp", "udp"]),
            "service": random.choice(["dns", "http", "ssl", "ssh", "smtp", "ftp"]),
            "duration": random.uniform(0.001, 60.0),
            "orig_bytes": random.randint(0, 10000),
            "resp_bytes": random.randint(0, 10000),
            "conn_state": random.choice(["SF", "S0", "S1", "S2", "S3", "REJ", "RSTO", "RSTOS0", "RSTR", "RSTRH", "SH", "SHR", "OTH"]),
            "local_orig": True,
            "local_resp": False,
            "missed_bytes": 0,
            "history": random.choice(["D", "ShADadFf", "ShADadF", "ShAD", "ShA", "Sh"]),
            "orig_pkts": random.randint(1, 50),
            "orig_ip_bytes": random.randint(64, 5000),
            "resp_pkts": random.randint(1, 50),
            "resp_ip_bytes": random.randint(64, 5000),
            "demo": True
        }
    
    async def _send_to_ingest(self, event):
        """Send event to ingest endpoint for proper logging."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.ingest_url,
                    headers={"Authorization": "Bearer TEST_KEY", "Content-Type": "application/json"},
                    json=event,
                    timeout=1.0
                )
                if response.status_code != 200:
                    log_system_event("demo_ingest_warning", f"Ingest endpoint returned {response.status_code}", {
                        "status_code": response.status_code
                    })
        except Exception as e:
            log_system_event("demo_ingest_error", f"Failed to send to ingest endpoint: {e}", {
                "error": str(e)
            })
            # Fallback to queue
            from ..pipeline import enqueue
            enqueue(event)
    
    async def _generator_loop(self):
        """Main generator loop that produces events at the specified EPS rate."""
        from ..pipeline import enqueue
        
        log_system_event("demo_start", f"Demo generator started: {DEMO_EPS} EPS for {DEMO_DURATION_SEC} seconds", {
            "eps": DEMO_EPS,
            "duration_sec": DEMO_DURATION_SEC,
            "variants": DEMO_VARIANTS
        })
        # Use timestamp for the generator loop
        self.start_time = time.time()
        
        # Calculate delay between events to achieve target EPS
        delay = 1.0 / DEMO_EPS
        
        while self.is_running:
            try:
                # Check if we've exceeded duration
                if time.time() - self.start_time > DEMO_DURATION_SEC:
                    log_system_event("demo_duration_reached", "Demo generator duration reached, stopping")
                    break
                
                # Generate events based on variants
                for variant in DEMO_VARIANTS:
                    if variant.strip() == "netflow":
                        event = self._generate_netflow_event()
                        # Send to ingest endpoint for proper logging
                        await self._send_to_ingest(event)
                    elif variant.strip() == "zeek":
                        event = self._generate_zeek_event()
                        # Send to ingest endpoint for proper logging
                        await self._send_to_ingest(event)
                
                # Wait for next event
                await asyncio.sleep(delay)
                
            except Exception as e:
                log_system_event("demo_error", f"Error in demo generator: {e}", {"error": str(e)})
                await asyncio.sleep(1)  # Wait before retrying
        
        log_system_event("demo_stop", "Demo generator stopped")
        self.is_running = False
    
    async def start(self) -> bool:
        """Start the demo generator."""
        if self.is_running:
            log_system_event("demo_warning", "Demo generator is already running")
            return False
        
        if not DEMO_MODE:
            log_system_event("demo_warning", "Demo mode is not enabled")
            return False
        
        try:
            # mark service start as soon as init succeeds
            self.start_time = datetime.now(timezone.utc)
            # existing logic to spin producer...
            self.is_running = True
            self.task = asyncio.create_task(self._generator_loop())
            log_system_event("demo_started", "Demo generator started successfully")
            return True
        except Exception:
            self.is_running = False
            return False
    
    async def stop(self) -> bool:
        """Stop the demo generator."""
        if not self.is_running:
            log_system_event("demo_warning", "Demo generator is not running")
            return False
        
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        log_system_event("demo_stopped", "Demo generator stopped successfully")
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the demo generator."""
        elapsed = time.time() - self.start_time.timestamp() if self.start_time else 0
        remaining = max(0, DEMO_DURATION_SEC - elapsed) if self.start_time else 0
        
        return {
            "running": self.is_running,
            "demo_mode": DEMO_MODE,
            "eps": DEMO_EPS,
            "duration_sec": DEMO_DURATION_SEC,
            "variants": DEMO_VARIANTS,
            "elapsed_sec": int(elapsed),
            "remaining_sec": int(remaining),
            "start_time": self.start_time
        }

# Global demo service instance
demo_service = DemoService()
