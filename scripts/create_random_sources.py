#!/usr/bin/env python3
import os, sys, json, time, random
import requests

# Configuration
API_BASE = "http://localhost/v1"
API_KEY = "DEV_ADMIN_KEY_5a8f9ffdc3"

# Random source data
SOURCE_NAMES = [
    "netflow-gw-01", "zeek-collector-02", "api-web-03", 
    "udp-sensor-04", "http-ingest-05", "syslog-relay-06"
]

DISPLAY_NAMES = [
    "Gateway NetFlow Collector", "Zeek Network Monitor", "Web API Ingest",
    "UDP Sensor Array", "HTTP Data Collector", "Syslog Relay Server"
]

COLLECTORS = [
    "gw-primary", "zeek-cluster", "api-gateway", 
    "udp-sensors", "http-collectors", "syslog-hub"
]

SITES = [
    "HQ", "Branch-01", "DC-East", "DC-West", "Cloud-Region", "Edge-Location"
]

TAGS = [
    ["production", "netflow"],
    ["monitoring", "zeek"],
    ["api", "web"],
    ["sensor", "udp"],
    ["collector", "http"],
    ["relay", "syslog"]
]

def create_random_source():
    """Create a random source with varied data"""
    source_id = random.choice(SOURCE_NAMES)
    source_type = random.choice(["udp", "http"])
    
    # Generate random IP ranges for allowed_ips
    allowed_ips = []
    for _ in range(random.randint(1, 3)):
        base_ip = f"{random.randint(10, 192)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
        cidr = f"{base_ip}.0/24"
        allowed_ips.append(cidr)
    
    source_data = {
        "id": source_id,
        "tenant_id": "default",
        "type": source_type,
        "display_name": random.choice(DISPLAY_NAMES),
        "collector": random.choice(COLLECTORS),
        "site": random.choice(SITES),
        "tags": json.dumps(random.choice(TAGS)),
        "health_status": random.choice(["healthy", "degraded", "stale"]),
        "status": random.choice(["enabled", "disabled"]),
        "allowed_ips": json.dumps(allowed_ips),
        "max_eps": random.randint(0, 10000),
        "block_on_exceed": random.choice([True, False]),
        "enabled": random.choice([True, False]),
        "eps_cap": random.randint(0, 5000),
        "notes": f"Random test source created at {int(time.time())}"
    }
    
    return source_data

def create_sources():
    """Create 6 random sources via API"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    created_sources = []
    
    for i in range(6):
        source_data = create_random_source()
        
        try:
            response = requests.post(
                f"{API_BASE}/sources",
                headers=headers,
                json=source_data
            )
            
            if response.status_code == 200:
                created_sources.append(source_data["id"])
                print(f"✅ Created source: {source_data['id']} ({source_data['type']})")
            else:
                print(f"❌ Failed to create {source_data['id']}: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Error creating {source_data['id']}: {e}")
    
    return created_sources

def main():
    print("Creating 6 random sources...")
    created = create_sources()
    
    print(f"\nCreated {len(created)} sources:")
    for source_id in created:
        print(f"  - {source_id}")
    
    # Verify by listing sources
    try:
        response = requests.get(
            f"{API_BASE}/sources?page=1&page_size=20",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nTotal sources in database: {data.get('total', 0)}")
        else:
            print(f"Failed to verify sources: {response.status_code}")
            
    except Exception as e:
        print(f"Error verifying sources: {e}")

if __name__ == "__main__":
    main()
