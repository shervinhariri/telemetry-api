"""
Admin Audit Service
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models.admin_audit import AdminAuditLog

logger = logging.getLogger(__name__)


def log_admin_action(
    actor_key_id: str,
    action: str,
    target: str,
    before_value: Optional[Dict[str, Any]] = None,
    after_value: Optional[Dict[str, Any]] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None
) -> None:
    """Log an admin action to the audit trail"""
    
    db = SessionLocal()
    try:
        audit_log = AdminAuditLog(
            actor_key_id=actor_key_id,
            action=action,
            target=target,
            before_value=json.dumps(before_value) if before_value else None,
            after_value=json.dumps(after_value) if after_value else None,
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        db.add(audit_log)
        db.commit()
        
        logger.info(f"Admin audit log: {actor_key_id} performed {action} on {target}")
        
    except Exception as e:
        logger.error(f"Failed to log admin action: {e}")
        db.rollback()
    finally:
        db.close()


def get_recent_audit_logs(limit: int = 100) -> list:
    """Get recent audit logs"""
    
    db = SessionLocal()
    try:
        logs = db.query(AdminAuditLog)\
                .order_by(AdminAuditLog.timestamp.desc())\
                .limit(limit)\
                .all()
        
        return [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "actor_key_id": log.actor_key_id,
                "action": log.action,
                "target": log.target,
                "before_value": json.loads(log.before_value) if log.before_value else None,
                "after_value": json.loads(log.after_value) if log.after_value else None,
                "client_ip": log.client_ip,
                "user_agent": log.user_agent
            }
            for log in logs
        ]
        
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        return []
    finally:
        db.close()
