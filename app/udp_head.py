"""
UDP Head component for Telemetry API
Handles UDP packet reception on port 8081 when FEATURE_UDP_HEAD is enabled
"""

import socket
import threading
import asyncio
import logging
import time
from typing import Optional
from contextlib import asynccontextmanager
from .config import FEATURES
from .metrics import prometheus_metrics

# Global state
_udp_socket: Optional[socket.socket] = None
_udp_thread: Optional[threading.Thread] = None
_udp_ready = False
_udp_bind_errors = 0
_udp_datagrams_total = 0
_udp_lock = threading.Lock()

logger = logging.getLogger("udp_head")

def get_udp_head_status() -> str:
    """Get UDP head status: 'disabled', 'ready', or 'error'"""
    if not FEATURES.get("udp_head", False):
        return "disabled"
    
    with _udp_lock:
        if _udp_ready:
            return "ready"
        elif _udp_bind_errors > 0:
            return "error"
        else:
            return "disabled"

def _udp_listener_loop():
    """Main UDP listener loop"""
    global _udp_socket, _udp_ready, _udp_bind_errors, _udp_datagrams_total
    
    try:
        # Create UDP socket
        _udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        _udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to port 8081
        _udp_socket.bind(("0.0.0.0", 8081))
        
        with _udp_lock:
            _udp_ready = True
            _udp_bind_errors = 0
        
        # Update Prometheus metrics
        prometheus_metrics.set_udp_head_ready(True)
        
        logger.info("UDP head bound successfully", extra={
            "component": "udp_head",
            "event": "bind_ready",
            "addr": ":8081"
        })
        
        # Set up rate limiting for debug logs
        last_debug_log = time.time()
        debug_log_interval = 5.0  # Log every 5 seconds max
        
        while True:
            try:
                # Receive datagram (non-blocking with timeout)
                _udp_socket.settimeout(1.0)
                data, addr = _udp_socket.recvfrom(65535)
                
                # Increment counters
                with _udp_lock:
                    _udp_datagrams_total += 1
                
                # Update Prometheus metrics
                prometheus_metrics.increment_udp_packets_received(1)
                prometheus_metrics.increment_udp_head_datagrams(1)
                
                # Rate-limited debug logging
                current_time = time.time()
                if current_time - last_debug_log >= debug_log_interval:
                    logger.debug("UDP datagram received", extra={
                        "component": "udp_head",
                        "event": "datagram_received",
                        "bytes": len(data),
                        "addr": f"{addr[0]}:{addr[1]}",
                        "total_datagrams": _udp_datagrams_total
                    })
                    last_debug_log = current_time
                
            except socket.timeout:
                # Timeout is expected, continue
                continue
            except Exception as e:
                logger.warning("UDP receive error", extra={
                    "component": "udp_head",
                    "event": "error",
                    "kind": "recv",
                    "msg": str(e)
                })
                prometheus_metrics.increment_udp_dropped("recv_error", 1)
                
    except Exception as e:
        with _udp_lock:
            _udp_ready = False
            _udp_bind_errors += 1
        
        # Update Prometheus metrics
        prometheus_metrics.set_udp_head_ready(False)
        prometheus_metrics.increment_udp_head_bind_errors(1)
        
        logger.warning("UDP head bind failed", extra={
            "component": "udp_head",
            "event": "error",
            "kind": "bind",
            "msg": str(e)
        })
        prometheus_metrics.increment_udp_dropped("bind_error", 1)

def start_udp_head():
    """Start UDP head if feature flag is enabled"""
    global _udp_thread
    
    if not FEATURES.get("udp_head", False):
        logger.info("UDP head disabled by feature flag", extra={
            "component": "udp_head",
            "event": "disabled"
        })
        return
    
    if _udp_thread and _udp_thread.is_alive():
        logger.warning("UDP head already running", extra={
            "component": "udp_head",
            "event": "already_running"
        })
        return
    
    logger.info("Starting UDP head", extra={
        "component": "udp_head",
        "event": "starting",
        "port": 8081
    })
    
    _udp_thread = threading.Thread(target=_udp_listener_loop, daemon=True)
    _udp_thread.start()

def stop_udp_head():
    """Stop UDP head and clean up resources"""
    global _udp_socket, _udp_thread, _udp_ready
    
    logger.info("Stopping UDP head", extra={
        "component": "udp_head",
        "event": "stopping"
    })
    
    # Close socket
    if _udp_socket:
        try:
            _udp_socket.close()
        except Exception as e:
            logger.warning("Error closing UDP socket", extra={
                "component": "udp_head",
                "event": "error",
                "kind": "close",
                "msg": str(e)
            })
        finally:
            _udp_socket = None
    
    # Reset state
    with _udp_lock:
        _udp_ready = False
        _udp_thread = None

def get_udp_stats() -> dict:
    """Get UDP head statistics"""
    with _udp_lock:
        return {
            "ready": _udp_ready,
            "bind_errors": _udp_bind_errors,
            "datagrams_total": _udp_datagrams_total,
            "port": 8081 if _udp_ready else None
        }
