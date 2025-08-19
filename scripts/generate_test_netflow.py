#!/usr/bin/env python3
"""
Simple NetFlow v5 test data generator
Generates basic NetFlow v5 packets for testing the collector
"""

import socket
import struct
import time
import random
import sys

def create_netflow_v5_packet(flows=1):
    """Create a NetFlow v5 packet with specified number of flows"""
    
    # NetFlow v5 header (24 bytes)
    version = 5
    count = flows
    sys_uptime = int(time.time() * 1000) % 0xFFFFFFFF
    unix_secs = int(time.time())
    unix_nsecs = int((time.time() % 1) * 1000000000)
    flow_sequence = random.randint(1, 0xFFFFFFFF)
    engine_type = 0
    engine_id = 0
    sampling_interval = 0
    
    header = struct.pack('!HHIIIIBBH',
        version, count, sys_uptime, unix_secs, unix_nsecs,
        flow_sequence, engine_type, engine_id, sampling_interval
    )
    
    # NetFlow v5 flow record (48 bytes each)
    flows_data = b''
    for i in range(flows):
        # Generate random flow data
        src_addr = random.randint(1, 0xFFFFFFFF)
        dst_addr = random.randint(1, 0xFFFFFFFF)
        nexthop = random.randint(1, 0xFFFFFFFF)
        input = random.randint(0, 0xFFFF)
        output = random.randint(0, 0xFFFF)
        packets = random.randint(1, 1000)
        octets = random.randint(64, 1500)
        first = random.randint(0, 0xFFFFFFFF)
        last = first + random.randint(1, 300)
        src_port = random.randint(1024, 65535)
        dst_port = random.randint(1, 65535)
        tcp_flags = random.randint(0, 0xFF)
        protocol = random.choice([1, 6, 17])  # ICMP, TCP, UDP
        tos = random.randint(0, 0xFF)
        src_as = random.randint(0, 0xFFFF)
        dst_as = random.randint(0, 0xFFFF)
        src_mask = random.randint(0, 32)
        dst_mask = random.randint(0, 32)
        flags = random.randint(0, 0xFFFF)
        
        flow_record = struct.pack('!IIIIHHIIIIHHBBHHBBH',
            src_addr, dst_addr, nexthop, input, output,
            packets, octets, first, last, src_port, dst_port,
            tcp_flags, protocol, tos, src_as, dst_as,
            src_mask, dst_mask, flags
        )
        flows_data += flow_record
    
    return header + flows_data

def send_netflow_data(host='127.0.0.1', port=2055, flows=1, count=1):
    """Send NetFlow test data to the collector"""
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"Sending {count} NetFlow packets with {flows} flows each to {host}:{port}")
    
    for i in range(count):
        packet = create_netflow_v5_packet(flows)
        sock.sendto(packet, (host, port))
        print(f"Sent packet {i+1}/{count} ({len(packet)} bytes)")
        time.sleep(0.1)  # Small delay between packets
    
    sock.close()
    print("Done!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate test NetFlow data')
    parser.add_argument('--host', default='127.0.0.1', help='Target host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=2055, help='Target port (default: 2055)')
    parser.add_argument('--flows', type=int, default=1, help='Flows per packet (default: 1)')
    parser.add_argument('--count', type=int, default=5, help='Number of packets to send (default: 5)')
    
    args = parser.parse_args()
    
    try:
        send_netflow_data(args.host, args.port, args.flows, args.count)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
