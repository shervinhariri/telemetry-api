# NetFlow/IPFIX Collector

The telemetry-api includes a NetFlow/IPFIX collector service that can receive and process network flow data from routers, switches, and other network devices.

## Overview

The collector service uses [GoFlow2](https://github.com/netsampler/goflow2) to collect NetFlow v5/v9 and IPFIX data, converting it to JSON format for easy processing and integration.

## Configuration

### Docker Compose Service

The collector is configured in `docker-compose.yml`:

```yaml
collector:
  image: netsampler/goflow2:latest
  command: ["-listen=netflow://:2055", "-format=json", "-transport=file", "-transport.file="]
  ports:
    - "2055:2055/udp"
  restart: unless-stopped
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
```

### Key Configuration Options

- **Listen Address**: `netflow://:2055` - Listens on UDP port 2055 for NetFlow data
- **Format**: `json` - Outputs flow records as line-delimited JSON
- **Transport**: `file` with empty file path outputs to STDOUT (docker logs)

## Usage

### Starting the Collector

```bash
# Start only the collector service
docker compose up -d collector

# Start all services including collector
docker compose up -d
```

### Monitoring Flow Data

```bash
# View real-time flow data
docker compose logs -f collector

# View recent flow records
docker compose logs collector | tail -20
```

### Testing the Collector

#### Using the Included Test Generator

```bash
# Generate and send test NetFlow data
python3 scripts/generate_test_netflow.py --count 5 --flows 3

# Run the comprehensive test script
./scripts/test_netflow.sh
```

#### Using External Tools

```bash
# Using nflowgen (if available)
nflowgen -r 1 -i 127.0.0.1:2055

# Using netflow-generator (if available)
netflow-generator -h 127.0.0.1 -p 2055 -r 1
```

## Flow Record Format

The collector outputs JSON flow records with the following structure:

```json
{
  "type": "NETFLOW_V5",
  "time_received_ns": 1755636366839794752,
  "sequence_num": 3915400858,
  "sampling_rate": 0,
  "sampler_address": "192.168.65.1",
  "time_flow_start_ns": 1755245595022470127,
  "time_flow_end_ns": 1755245595051470127,
  "bytes": 66,
  "packets": 2176909475,
  "src_addr": "193.192.249.98",
  "dst_addr": "195.43.108.180",
  "etype": "IPv4",
  "proto": "HOPOPT",
  "src_port": 0,
  "dst_port": 3894,
  "in_if": 0,
  "out_if": 7451,
  "src_mac": "00:00:00:00:00:00",
  "dst_mac": "00:00:00:00:00:00",
  "src_vlan": 0,
  "dst_vlan": 0,
  "vlan_id": 0,
  "ip_tos": 233,
  "forwarding_status": 0,
  "ip_ttl": 0,
  "ip_flags": 0,
  "tcp_flags": 63,
  "icmp_type": 0,
  "icmp_code": 0,
  "ipv6_flow_label": 0,
  "fragment_id": 0,
  "fragment_offset": 0,
  "src_as": 317,
  "dst_as": 24552,
  "next_hop": "253.147.37.253",
  "next_hop_as": 0,
  "src_net": "invalid Prefix",
  "dst_net": "invalid Prefix",
  "bgp_next_hop": "",
  "bgp_communities": [],
  "as_path": [],
  "mpls_ttl": [],
  "mpls_label": [],
  "mpls_ip": [],
  "observation_domain_id": 0,
  "observation_point_id": 0,
  "layer_stack": [],
  "layer_size": [],
  "ipv6_routing_header_addresses": [],
  "ipv6_routing_header_seg_left": 0
}
```

## Network Device Configuration

### Cisco IOS

```cisco
! Configure NetFlow export
ip flow-export destination 192.168.1.100 2055
ip flow-export version 5
ip flow-export source Loopback0

! Enable NetFlow on interfaces
interface GigabitEthernet0/0
 ip flow ingress
 ip flow egress
```

### Juniper JunOS

```junos
services {
    flow-monitoring {
        version5 {
            template ipv4-template;
            export-rate 1;
        }
    }
}
forwarding-options {
    sampling {
        input {
            rate 1000;
        }
        family inet {
            output {
                flow-server 192.168.1.100 {
                    port 2055;
                    autonomous-system-type origin;
                    version 5;
                }
            }
        }
    }
}
```

### MikroTik RouterOS

```routeros
/ip flow
set enabled=yes
/ip flow export
add dst-address=192.168.1.100 dst-port=2055 version=5
```

## Integration with Telemetry API

The collector can be integrated with the telemetry-api by:

1. **Direct Integration**: Modify the collector to send data to the API's `/v1/ingest` endpoint
2. **Log Processing**: Process the JSON logs and forward to the API
3. **Pipeline Integration**: Use the flow data as input for the telemetry pipeline

## Troubleshooting

### Common Issues

1. **No flow records received**
   - Check if the collector is running: `docker compose ps collector`
   - Verify UDP port 2055 is accessible: `netstat -uln | grep 2055`
   - Check network device configuration

2. **Invalid flow data**
   - Verify NetFlow version compatibility (v5/v9/IPFIX)
   - Check network device export settings
   - Review collector logs for parsing errors

3. **High resource usage**
   - Adjust sampling rate on network devices
   - Consider filtering flows at the source
   - Monitor collector performance metrics

### Log Analysis

```bash
# Check collector status
docker compose logs collector | grep -E "(starting|error|warning)"

# Count flow records
docker compose logs collector | grep -c "NETFLOW_V5"

# Monitor real-time activity
docker compose logs -f collector | grep "NETFLOW_V5"
```

## Performance Considerations

- **Sampling Rate**: Use appropriate sampling rates to balance detail vs. performance
- **Flow Volume**: Monitor the number of flows per second to ensure collector can handle the load
- **Storage**: Consider log rotation and retention policies for long-term operation
- **Network**: Ensure sufficient bandwidth for flow export traffic

## Security

- **Network Access**: Restrict access to UDP port 2055 to authorized network devices only
- **Authentication**: Consider implementing flow authentication if supported by your devices
- **Monitoring**: Monitor for unusual flow patterns or excessive export traffic
