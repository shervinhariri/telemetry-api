#!/usr/bin/env python3
"""
NetFlow to Telemetry API Mapper

Reads goflow2 JSON lines from stdin and maps them to flows.v1 format,
then batches and posts them to the telemetry API ingest endpoint.
"""

import os
import sys
import json
import time
import gzip
import signal
import logging
from typing import Dict, List, Optional
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '200'))
FLUSH_INTERVAL = int(os.getenv('FLUSH_INTERVAL', '1'))  # seconds
MAX_RECORDS_PER_BATCH = int(os.getenv('MAX_RECORDS_PER_BATCH', '10000'))
MAX_PAYLOAD_SIZE = int(os.getenv('MAX_PAYLOAD_SIZE', '5242880'))  # 5MB
GZIP_THRESHOLD = int(os.getenv('GZIP_THRESHOLD', '51200'))  # 50KB

# API Configuration
API_BASE = os.getenv('API', 'http://telemetry-api:8080')
API_KEY = os.getenv('KEY', 'TEST_KEY')
COLLECTOR_ID = os.getenv('COLLECTOR_ID', 'gw-local')

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class NetFlowMapper:
    def __init__(self):
        self.batch: List[Dict] = []
        self.last_flush = time.time()
        self.total_sent = 0
        self.total_records = 0
        self.session = self._create_session()
        
        # Signal handling for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, flushing remaining batch...")
        self.flush_batch()
        sys.exit(0)
    
    def map_netflow_to_flows_v1(self, netflow_record: Dict) -> Optional[Dict]:
        """Map goflow2 NetFlow record to flows.v1 format"""
        try:
            # Extract basic flow information
            flow = {
                "ts": int(netflow_record.get("time_flow_start_ns", 0)) // 1000000000,  # Convert ns to seconds
                "src_ip": netflow_record.get("src_addr", ""),
                "dst_ip": netflow_record.get("dst_addr", ""),
                "src_port": netflow_record.get("src_port", 0),
                "dst_port": netflow_record.get("dst_port", 0),
                "proto": self._map_protocol(netflow_record.get("proto", "")),
                "bytes": netflow_record.get("bytes", 0),
                "packets": netflow_record.get("packets", 0),
            }
            
            # Add optional interface information
            if netflow_record.get("in_if"):
                flow["ingress_if"] = netflow_record["in_if"]
            if netflow_record.get("out_if"):
                flow["egress_if"] = netflow_record["out_if"]
            
            # Validate required fields
            if not flow["src_ip"] or not flow["dst_ip"]:
                return None
            
            return flow
            
        except Exception as e:
            logger.warning(f"Failed to map NetFlow record: {e}")
            return None
    
    def _map_protocol(self, proto: str) -> int:
        """Map protocol string to numeric value"""
        protocol_map = {
            "ICMP": 1,
            "TCP": 6,
            "UDP": 17,
            "HOPOPT": 0,
            "IPv6-Route": 43,
            "unassigned": 0
        }
        return protocol_map.get(proto, 0)
    
    def add_to_batch(self, flow: Dict):
        """Add flow to current batch"""
        self.batch.append(flow)
        
        # Check if we should flush
        if len(self.batch) >= BATCH_SIZE:
            self.flush_batch()
        elif time.time() - self.last_flush >= FLUSH_INTERVAL:
            self.flush_batch()
    
    def flush_batch(self):
        """Flush current batch to API"""
        if not self.batch:
            return
        
        # Ensure we don't exceed record limits
        if len(self.batch) > MAX_RECORDS_PER_BATCH:
            logger.warning(f"Batch size {len(self.batch)} exceeds limit {MAX_RECORDS_PER_BATCH}, truncating")
            self.batch = self.batch[:MAX_RECORDS_PER_BATCH]
        
        # Prepare payload
        payload = {
            "records": self.batch,
            "collector_id": COLLECTOR_ID,
            "format": "flows.v1"
        }
        
        # Serialize to JSON
        json_data = json.dumps(payload, separators=(',', ':'))
        payload_size = len(json_data.encode('utf-8'))
        
        # Determine if we should gzip
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        if payload_size > GZIP_THRESHOLD:
            # Gzip the payload
            gzipped_data = gzip.compress(json_data.encode('utf-8'))
            if len(gzipped_data) > MAX_PAYLOAD_SIZE:
                logger.error(f"Gzipped payload size {len(gzipped_data)} exceeds limit {MAX_PAYLOAD_SIZE}")
                return
            
            headers["Content-Encoding"] = "gzip"
            data = gzipped_data
            logger.debug(f"Gzipped payload: {payload_size} -> {len(gzipped_data)} bytes")
        else:
            if payload_size > MAX_PAYLOAD_SIZE:
                logger.error(f"Payload size {payload_size} exceeds limit {MAX_PAYLOAD_SIZE}")
                return
            data = json_data
        
        # Send to API
        try:
            response = self.session.post(
                f"{API_BASE}/v1/ingest",
                data=data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"[INGEST] sent {len(self.batch)} status={response.status_code}")
                self.total_sent += 1
                self.total_records += len(self.batch)
            elif response.status_code == 413:
                logger.warning(f"[INGEST][ERR] Payload too large (413), splitting batch")
                # Split batch in half and retry
                mid = len(self.batch) // 2
                self.batch = self.batch[mid:]  # Keep second half
                self.flush_batch()  # Retry with smaller batch
                return
            else:
                logger.error(f"[INGEST][ERR] HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[INGEST][ERR] Request failed: {e}")
        
        # Clear batch and update timestamp
        self.batch = []
        self.last_flush = time.time()
    
    def process_line(self, line: str):
        """Process a single line of NetFlow JSON"""
        try:
            # Strip container prefix if present (e.g., "collector-1  | ")
            clean_line = line.strip()
            if "|" in clean_line:
                clean_line = clean_line.split("|", 1)[1].strip()
            
            # Parse JSON
            netflow_record = json.loads(clean_line)
            
            # Check if it's a NetFlow record
            if netflow_record.get("type") not in ["NETFLOW_V5", "NETFLOW_V9", "IPFIX"]:
                return
            
            # Map to flows.v1 format
            flow = self.map_netflow_to_flows_v1(netflow_record)
            if flow:
                self.add_to_batch(flow)
                
        except json.JSONDecodeError:
            logger.debug(f"Invalid JSON line: {line.strip()}")
        except Exception as e:
            logger.warning(f"Error processing line: {e}")
    
    def run(self):
        """Main processing loop"""
        logger.info(f"Starting NetFlow mapper (batch_size={BATCH_SIZE}, flush_interval={FLUSH_INTERVAL}s)")
        logger.info(f"API: {API_BASE}, Collector ID: {COLLECTOR_ID}")
        
        try:
            for line in sys.stdin:
                self.process_line(line)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
        finally:
            # Flush any remaining records
            if self.batch:
                logger.info(f"Flushing final batch of {len(self.batch)} records...")
                self.flush_batch()
            
            logger.info(f"Mapper finished. Total batches: {self.total_sent}, Total records: {self.total_records}")

def main():
    mapper = NetFlowMapper()
    mapper.run()

if __name__ == "__main__":
    main()
