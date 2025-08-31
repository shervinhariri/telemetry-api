"""
Risk scoring module
Calculates risk scores based on threat intelligence matches and other factors
"""

from typing import Any, Dict, List
import ipaddress

RISKY_PORTS = {3389, 445}  # RDP, SMB
BYTES_THRESHOLD = 2_000_000  # 2MB

def _ip_in_list(ip: str, matches: List[Any]) -> bool:
    """Accept either list of dicts (with 'value' or 'cidr') or strings (CIDR/IP)."""
    if not ip:
        return False
    for m in matches or []:
        if isinstance(m, dict):
            cidr = m.get("value") or m.get("cidr")
        else:
            cidr = str(m)
        try:
            if "/" in cidr:
                if ipaddress.ip_address(ip) in ipaddress.ip_network(cidr, strict=False):
                    return True
            else:
                if ip == cidr:
                    return True
        except Exception:
            continue
    return False

def _normalize(record: Dict[str, Any]) -> Dict[str, Any]:
    # Accept NetFlow-ish and Zeek conn-ish fields
    src_ip = record.get("src_ip") or record.get("id_orig_h") or record.get("id.orig_h")
    dst_ip = record.get("dst_ip") or record.get("id_resp_h") or record.get("id.resp_h")
    dst_port = (
        record.get("dst_port")
        or record.get("id_resp_p")
        or record.get("id.resp_p")
    )
    # bytes can be in different fields
    bytes_total = record.get("bytes")
    if bytes_total is None:
        # zeek conn approximation: orig_bytes + resp_bytes
        ob = record.get("orig_bytes")
        rb = record.get("resp_bytes")
        if ob is not None or rb is not None:
            try:
                bytes_total = int(ob or 0) + int(rb or 0)
            except Exception:
                bytes_total = None
    return {"src_ip": src_ip, "dst_ip": dst_ip, "dst_port": dst_port, "bytes": bytes_total}

def clamp(n: int, lo=0, hi=100) -> int:
    return max(lo, min(hi, n))

def score(record: Dict[str, Any], ti_matches: List[Any]) -> int:
    """
    Contract: if ti_matches is non-empty, the event ALREADY matched threat intel.
    Do not try to re-evaluate CIDRs here.
    """
    r = _normalize(record)
    s = 10  # base

    # TI boost: any non-empty match list means matched
    if ti_matches:
        s += 60

    # risky destination ports
    if r["dst_port"] in RISKY_PORTS:
        s += 10

    # large transfer bytes
    if isinstance(r["bytes"], (int, float)) and r["bytes"] >= BYTES_THRESHOLD:
        s += 10

    return clamp(int(s))
