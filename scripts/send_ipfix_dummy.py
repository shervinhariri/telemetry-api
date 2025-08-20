#!/usr/bin/env python3
"""
Send dummy IPFIX packets for UDP admission control testing
"""

import socket
import struct
import time
import random
import argparse
from typing import List

def create_dummy_ipfix_packet(sequence: int = 1) -> bytes:
    """Create a dummy IPFIX packet"""
    
    # IPFIX Header (16 bytes)
    version = 10  # IPFIX version
    length = 40   # Total packet length
    export_time = int(time.time())
    sequence_number = sequence
    observation_domain_id = 1
    
    header = struct.pack('!HHIII', version, length, export_time, sequence_number, observation_domain_id)
    
    # IPFIX Data Set Header (4 bytes)
    set_id = 256  # Template set
    set_length = 24
    
    set_header = struct.pack('!HH', set_id, set_length)
    
    # Template Record (4 bytes)
    template_id = 256
    field_count = 0
    
    template_record = struct.pack('!HH', template_id, field_count)
    
    return header + set_header + template_record

def send_udp_packets(host: str, port: int, count: int, delay: float = 0.1, source_ip: str = None):
    """Send UDP packets to the specified host and port"""
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    if source_ip:
        # Bind to specific source IP if provided
        sock.bind((source_ip, 0))
    
    print(f"Sending {count} UDP packets to {host}:{port}")
    
    for i in range(count):
        packet = create_dummy_ipfix_packet(i + 1)
        sock.sendto(packet, (host, port))
        
        if i % 10 == 0:
            print(f"Sent packet {i+1}/{count}")
        
        if delay > 0:
            time.sleep(delay)
    
    sock.close()
    print(f"Sent {count} packets successfully")

def main():
    parser = argparse.ArgumentParser(description='Send dummy IPFIX packets for testing')
    parser.add_argument('--host', default='localhost', help='Target host (default: localhost)')
    parser.add_argument('--port', type=int, default=2055, help='Target port (default: 2055)')
    parser.add_argument('--count', type=int, default=10, help='Number of packets to send (default: 10)')
    parser.add_argument('--delay', type=float, default=0.1, help='Delay between packets in seconds (default: 0.1)')
    parser.add_argument('--source-ip', help='Source IP address to bind to')
    parser.add_argument('--flood', action='store_true', help='Send packets rapidly (no delay)')
    
    args = parser.parse_args()
    
    if args.flood:
        args.delay = 0
    
    try:
        send_udp_packets(args.host, args.port, args.count, args.delay, args.source_ip)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
