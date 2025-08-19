#!/usr/bin/env python3
"""
Test script for the NetFlow mapper
"""

import json
import subprocess
import sys
import os

# Sample NetFlow record
sample_netflow = {
    "type": "NETFLOW_V5",
    "time_received_ns": 1755636798755486758,
    "sequence_num": 2733219910,
    "sampling_rate": 0,
    "sampler_address": "192.168.65.1",
    "time_flow_start_ns": 1752346656596209922,
    "time_flow_end_ns": 1754314853007209922,
    "bytes": 562102876,
    "packets": 58467,
    "src_addr": "7.6.191.82",
    "dst_addr": "153.186.70.134",
    "etype": "IPv4",
    "proto": "unassigned",
    "src_port": 30032,
    "dst_port": 19675,
    "in_if": 51730,
    "out_if": 23429,
    "src_mac": "00:00:00:00:00:00",
    "dst_mac": "00:00:00:00:00:00",
    "src_vlan": 0,
    "dst_vlan": 0,
    "vlan_id": 0,
    "ip_tos": 144,
    "forwarding_status": 0,
    "ip_ttl": 0,
    "ip_flags": 0,
    "tcp_flags": 0,
    "icmp_type": 0,
    "icmp_code": 0,
    "ipv6_flow_label": 0,
    "fragment_id": 0,
    "fragment_offset": 0,
    "src_as": 52250,
    "dst_as": 15,
    "next_hop": "123.181.13.178",
    "next_hop_as": 0,
    "src_net": "4.0.0.0/6",
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

def test_mapper():
    """Test the mapper with sample data"""
    print("Testing NetFlow mapper...")
    
    # Convert sample to JSON line
    json_line = json.dumps(sample_netflow)
    print(f"Input: {json_line}")
    
    # Run mapper with sample data
    try:
        result = subprocess.run(
            [sys.executable, "nf2ingest.py"],
            input=json_line + "\n",
            text=True,
            capture_output=True,
            timeout=30
        )
        
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("Mapper timed out")
        return False
    except Exception as e:
        print(f"Error running mapper: {e}")
        return False

if __name__ == "__main__":
    success = test_mapper()
    sys.exit(0 if success else 1)
