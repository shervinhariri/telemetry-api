from typing import Tuple, List, Dict, Any
import ipaddress

COMMON_DNS = 53
COMMON_HTTP = 80
COMMON_HTTPS = 443

class RiskScorer:
    def score(self, enriched_record: Dict[str, Any]) -> Tuple[int, List[str]]:
        score = 0
        reasons = []

        # Threat match boosts heavily
        t = enriched_record.get("threat", {})
        if t.get("matched"):
            m = t.get("matches", [])
            worst = max((x.get("confidence", 0) for x in m), default=0)
            inc = 20 + int(worst / 5)  # 20..40 approx
            score += inc
            reasons.append(f"Threat list match (max confidence {worst}) +{inc}")

        # Destination to public IP with high resp_bytes
        dst_ip = enriched_record.get("id_resp_h")
        try:
            if dst_ip and ipaddress.ip_address(dst_ip).is_global:
                rb = enriched_record.get("resp_bytes", 0) or 0
                if rb > 10_000:
                    score += 10
                    reasons.append("High response bytes to public IP +10")
        except Exception:
            pass

        # Uncommon destination port
        dst_p = enriched_record.get("id_resp_p")
        if dst_p and dst_p not in (COMMON_DNS, COMMON_HTTP, COMMON_HTTPS):
            score += 5
            reasons.append("Uncommon destination port +5")

        # Cap 0..100
        score = max(0, min(100, score))
        return score, reasons
