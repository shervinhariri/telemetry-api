"""
Admin Security API endpoints for firewall and security management
"""

from fastapi import APIRouter, HTTPException, Request, Query, Depends
import subprocess
import tempfile
import json
import logging
from typing import List, Dict, Any

from ..services.sources import sources_cache
from ..services.audit import log_admin_action
from ..db import SessionLocal
from ..models.source import Source
from ..auth import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/security", tags=["admin"], dependencies=[Depends(require_admin)])

def list_enabled_sources() -> List[Dict[str, Any]]:
    """Get all enabled sources with their allowed IPs"""
    db = SessionLocal()
    try:
        sources = db.query(Source).filter(Source.status == "enabled").all()
        result = []
        for source in sources:
            try:
                allowed_ips = json.loads(source.allowed_ips) if source.allowed_ips else []
                result.append({
                    "id": source.id,
                    "allowed_ips": allowed_ips,
                    "status": source.status
                })
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid allowed_ips for source {source.id}: {e}")
                continue
        return result
    finally:
        db.close()

@router.post("/sync-allowlist")
async def sync_allowlist(request: Request, dry_run: bool = Query(False, description="Preview changes without applying")):
    """Sync nftables allowlist with enabled sources"""
    try:
        import os
        from datetime import datetime
        
        # Get UDP port from environment
        udp_port = os.getenv("UDP_PORT", "2055")
        
        # Check if nftables is available first
        import shutil
        if not shutil.which("nft"):
            return {
                "status": "nftables_not_available",
                "message": "nftables not available on this system",
                "ipv4_cidrs": [],
                "ipv6_cidrs": [],
                "dry_run": dry_run
            }
        
        # Get enabled sources
        sources = list_enabled_sources()
        
        # Extract CIDRs
        cidrs_v4 = set()
        cidrs_v6 = set()
        
        for source in sources:
            allowed_ips = source.get("allowed_ips", [])
            if isinstance(allowed_ips, str):
                try:
                    allowed_ips = json.loads(allowed_ips)
                except json.JSONDecodeError:
                    allowed_ips = []
            
            for cidr in allowed_ips:
                if ":" in cidr:  # IPv6
                    cidrs_v6.add(cidr)
                else:  # IPv4
                    cidrs_v4.add(cidr)
        
        # Generate nftables script
        script_lines = []
        
        # IPv4 set
        script_lines.append("flush set inet telemetry exporters")
        if cidrs_v4:
            script_lines.append(f"add element inet telemetry exporters {{ {', '.join(cidrs_v4)} }}")
        
        # IPv6 set (optional)
        script_lines.append("flush set inet telemetry exporters6")
        if cidrs_v6:
            script_lines.append(f"add element inet telemetry exporters6 {{ {', '.join(cidrs_v6)} }}")
        
        script = "\n".join(script_lines)
        
        if dry_run:
            return {
                "status": "dry_run",
                "message": "Preview of nftables changes",
                "ipv4_added": len(cidrs_v4),
                "ipv6_added": len(cidrs_v6),
                "ipv4_cidrs": list(cidrs_v4),
                "ipv6_cidrs": list(cidrs_v6),
                "nft_script": script,
                "dry_run": True
            }
        
        # Write script to temporary file
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".nft") as f:
            f.write(script)
            script_path = f.name
        
        # Execute nftables command
        try:
            result = subprocess.run(
                ["nft", "-f", script_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"nftables sync successful: {len(cidrs_v4)} IPv4, {len(cidrs_v6)} IPv6 CIDRs")
            
            # Log the firewall sync action
            api_key_id = getattr(request.state, 'api_key_id', 'unknown')
            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get('user-agent')
            
            log_admin_action(
                actor_key_id=api_key_id,
                action="firewall_sync",
                target="nftables_allowlist",
                after_value={
                    "ipv4_added": len(cidrs_v4),
                    "ipv6_added": len(cidrs_v6),
                    "total_sources": len(sources)
                },
                client_ip=client_ip,
                user_agent=user_agent
            )
            
            return {
                "status": "success",
                "ipv4_added": len(cidrs_v4),
                "ipv6_added": len(cidrs_v6),
                "total_sources": len(sources),
                "message": f"Synced {len(cidrs_v4)} IPv4 and {len(cidrs_v6)} IPv6 CIDRs to nftables",
                "last_sync_time": datetime.utcnow().isoformat(),
                "dry_run": False
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"nftables sync failed: {e.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"nftables sync failed: {e.stderr}"
            )
        finally:
            # Clean up temporary file
            try:
                os.unlink(script_path)
            except OSError:
                pass
                
    except Exception as e:
        logger.error(f"Allowlist sync error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Allowlist sync failed: {str(e)}"
        )

@router.get("/allowlist/status")
async def get_allowlist_status(request: Request):
    """Get current allowlist status and statistics"""
    # Check if user has admin scope
    scopes = getattr(request.state, 'scopes', [])
    if "admin" not in scopes:
        raise HTTPException(status_code=403, detail="Admin scope required")
    
    try:
        import shutil
        import os
        from datetime import datetime
        
        # Get UDP port from environment
        udp_port = os.getenv("UDP_PORT", "2055")
        
        # 1) Report nft availability
        nft_exists = shutil.which("nft") is not None
        status = {
            "nft_available": nft_exists,
            "udp_port": udp_port,
            "ipv4_count": 0, 
            "ipv6_count": 0, 
            "synced": False,
            "last_sync_time": None,
            "last_sync_counts": {"ipv4": 0, "ipv6": 0}
        }
        
        # 2) If nft exists, optionally parse current set to count elements (best-effort)
        if nft_exists:
            try:
                out = subprocess.run(
                    ["nft", "list", "set", "inet", "telemetry", "exporters"],
                    check=True, capture_output=True, text=True
                ).stdout
                # very simple count parse (optional):
                status["ipv4_count"] = out.count("element")
                status["synced"] = True
            except subprocess.CalledProcessError:
                status["synced"] = False
            except FileNotFoundError:
                status["synced"] = False
        
        # Get enabled sources for additional context
        sources = list_enabled_sources()
        status["enabled_sources"] = len(sources)
        status["configured_ipv4_cidrs"] = sum(
            len([c for c in s.get("allowed_ips", []) if ":" not in c])
            for s in sources
        )
        status["configured_ipv6_cidrs"] = sum(
            len([c for c in s.get("allowed_ips", []) if ":" in c])
            for s in sources
        )
        
        return status
        
    except Exception as e:
        logger.error(f"Allowlist status error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Allowlist status failed: {str(e)}"
        )
