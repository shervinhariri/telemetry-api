# Sample Data Files

This directory contains example data files for testing the Telemetry API.

## 📁 Available Samples

### `zeek_conn.json`
Zeek connection log data in the standard Zeek format.
```json
{
  "collector_id": "lab-zeek-1",
  "format": "zeek.conn.v1",
  "records": [...]
}
```

**Usage:**
```bash
curl -X POST http://localhost/v1/ingest \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data @samples/zeek_conn.json
```

### `flows_v1.json`
Network flow data in the flows.v1 format.
```json
{
  "collector_id": "lab-flows-1",
  "format": "flows.v1",
  "records": [...]
}
```

**Usage:**
```bash
curl -X POST http://localhost/v1/ingest \
  -H "Authorization: Bearer TEST_KEY" \
  -H "Content-Type: application/json" \
  --data @samples/flows_v1.json
```

## 🧪 Testing

Use these samples with the test script:
```bash
./scripts/test_api.sh
```

The test script will automatically use `zeek_conn.json` for ingest testing.

## 📊 Data Formats

### Zeek Connection Format
- **Source**: Zeek network security monitor
- **Fields**: Connection metadata, bytes, packets, duration
- **Use Case**: Network traffic analysis, security monitoring

### Flows Format
- **Source**: NetFlow, sFlow, or similar flow collectors
- **Fields**: Source/destination IPs, ports, protocols, bytes
- **Use Case**: Network traffic analysis, capacity planning

## 🔧 Customization

You can modify these samples or create your own following the same format:

1. **Required fields**: `ts` (timestamp), `src_ip`, `dst_ip`
2. **Optional fields**: `src_port`, `dst_port`, `proto`, `bytes`, `packets`
3. **Format**: JSON with `records` array containing flow objects

## 📝 Notes

- All timestamps should be in Unix epoch format
- IP addresses should be valid IPv4 or IPv6
- Port numbers should be 1-65535
- Protocols should be standard (tcp, udp, icmp, etc.)
