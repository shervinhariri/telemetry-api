import os
import time
import json
import gzip
import socket
import asyncio
import aiohttp
import uuid
from collections import defaultdict

API_URL = os.getenv("API_URL", "http://api-core:80/v1/ingest/netflow")
API_KEY = os.getenv("API_KEY", "")
SOURCE_ID = os.getenv("SOURCE_ID", "udp-head-default")
UDP_BIND = os.getenv("UDP_BIND", "0.0.0.0")
UDP_PORT = int(os.getenv("UDP_PORT", "2055"))
ALLOWLIST = [x.strip() for x in os.getenv("ALLOWLIST_CIDRS", "").split(",") if x.strip()]
RATE_PER_MIN = int(os.getenv("RATE_PER_MIN", "60000"))

# TODO: implement fast CIDR check; for now allow all if list empty
def allowed(ip: str) -> bool:
    return True if not ALLOWLIST else ip in ALLOWLIST  # replace with CIDR match

rate = defaultdict(lambda: {"win": 0, "count": 0})
metrics = {"udp_admitted_total": 0, "udp_dropped_total": defaultdict(int)}

def admit(ip: str) -> bool:
    if not allowed(ip):
        metrics["udp_dropped_total"]["not_allowlisted"] += 1
        return False
    now = int(time.time() // 60)
    s = rate[ip]
    if s["win"] != now:
        s["win"], s["count"] = now, 0
    s["count"] += 1
    if s["count"] > RATE_PER_MIN:
        metrics["udp_dropped_total"]["rate_limited"] += 1
        return False
    metrics["udp_admitted_total"] += 1
    return True

async def post_batch(batch):
    if not batch:
        return
    
    # Generate trace ID for this batch
    trace_id = str(uuid.uuid4())
    
    body = {"format": "flows.v1", "records": batch}
    data = gzip.compress(json.dumps(body).encode())
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Content-Encoding": "gzip",
        "X-Source-Id": SOURCE_ID,
        "X-Request-ID": trace_id,
    }
    
    print(f"Mapper sending batch with trace_id: {trace_id}")
    
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(API_URL, data=data, headers=headers, timeout=15) as r:
                if r.status >= 300:
                    metrics["udp_dropped_total"][f"http_{r.status}"] += 1
                    print(f"Mapper HTTP error {r.status} for trace_id: {trace_id}")
                else:
                    print(f"Mapper success for trace_id: {trace_id}")
    except Exception as e:
        metrics["udp_dropped_total"]["http_error"] += 1
        print(f"Mapper exception for trace_id {trace_id}: {e}")

# NOTE: placeholder decoder; wire in your NetFlow/IPFIX decoder here
def decode_to_flows(records_bytes: bytes, src_ip: str):
    # return list of dicts with minimal required fields:
    # ts, src_ip, src_port, dst_ip, dst_port, proto, bytes, packets, duration
    return []

class ServerProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.buffer = []

    def datagram_received(self, data, addr):
        ip, _ = addr
        if not admit(ip):
            return
        flows = decode_to_flows(data, ip)
        if not flows:
            return
        self.buffer.extend(flows)
        if len(self.buffer) >= 500:  # flush chunk
            asyncio.create_task(post_batch(self.buffer[:500]))
            self.buffer = self.buffer[500:]

async def metrics_reporter():
    # Placeholder: could POST metrics to api-core if needed
    while True:
        await asyncio.sleep(10)

async def main():
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: ServerProtocol(), local_addr=(UDP_BIND, UDP_PORT)
    )
    try:
        # Run a simple background reporter
        asyncio.create_task(metrics_reporter())
        while True:
            await asyncio.sleep(5)
    finally:
        transport.close()

if __name__ == "__main__":
    asyncio.run(main())


