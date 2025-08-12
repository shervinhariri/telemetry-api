from typing import List, Dict, Any
import ipaddress
import csv
from pathlib import Path

class ThreatMatcher:
    def __init__(self, csv_path: str):
        self.rules = []  # list of (ip_network, category, confidence)
        p = Path(csv_path)
        if p.exists():
            with p.open() as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cidr = row.get("ip_or_cidr")
                    cat = row.get("category", "unknown")
                    conf = int(row.get("confidence", "50") or 50)
                    try:
                        net = ipaddress.ip_network(cidr, strict=False)
                        self.rules.append((net, cat, conf))
                    except Exception:
                        # attempt single IP
                        try:
                            ip = ipaddress.ip_address(cidr)
                            net = ipaddress.ip_network(f"{ip}/32", strict=False)
                            self.rules.append((net, cat, conf))
                        except Exception:
                            continue

    def match_any(self, ips: List[str]) -> List[Dict[str, Any]]:
        results = []
        for ip_str in ips:
            try:
                ip = ipaddress.ip_address(ip_str)
            except Exception:
                continue
            for net, cat, conf in self.rules:
                if ip in net:
                    results.append({"ip": ip_str, "match": str(net), "category": cat, "confidence": conf})
        return results
