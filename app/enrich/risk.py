from typing import Dict, Any, List

class RiskScorer:
    def __init__(self):
        # Risky destination ports
        self.risky_ports = {23, 445, 1433, 3389}
        
    def score(self, event: Dict[str, Any], ti_matches: List[str]) -> int:
        """
        Calculate risk score for an event
        
        Deterministic v1 rubric:
        - Base = 10
        - +60 if TI match
        - +10 if dst_port in {23,445,1433,3389} or src_port ephemeral + high bytes
        - +5 if geo country != tenant_country (if available)
        - Clamp 0..100
        """
        score = 10  # Base score
        
        # Threat intelligence match (heaviest weight)
        if ti_matches:
            score += 60
            
        # Risky destination ports
        dst_port = event.get('dst_port') or event.get('id_resp_p')
        if dst_port and dst_port in self.risky_ports:
            score += 10
            
        # High bytes with ephemeral source port
        src_port = event.get('src_port') or event.get('id_orig_p')
        bytes_field = event.get('bytes') or event.get('orig_bytes', 0) or event.get('resp_bytes', 0)
        
        if src_port and bytes_field:
            # Check if source port is ephemeral (1024-65535) and bytes > 1MB
            if 1024 <= src_port <= 65535 and bytes_field > 1_000_000:
                score += 10
                
        # Geographic risk (if tenant country is available)
        # This would require tenant context - for now, skip this factor
        # tenant_country = get_tenant_country()
        # geo_country = event.get('geo', {}).get('country')
        # if tenant_country and geo_country and geo_country != tenant_country:
        #     score += 5
            
        # Clamp to 0-100 range
        return max(0, min(100, score))

# Global instance
risk_scorer = RiskScorer()

def score(event: Dict[str, Any], ti_matches: List[str]) -> int:
    """Convenience function to score an event"""
    return risk_scorer.score(event, ti_matches)
