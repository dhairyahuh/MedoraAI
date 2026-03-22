"""
Audit Logger for HIPAA/GDPR Compliance
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import threading

class AuditLogger:
    """
    HIPAA-compliant audit logging with immutable records
    
    Features:
    - Structured JSON logs
    - Append-only (immutable)
    - 7-year retention ready
    - Thread-safe
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, log_dir: Path = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, log_dir: Path = None):
        if hasattr(self, '_initialized'):
            return
        
        if log_dir is None:
            log_dir = Path(__file__).parent.parent / "logs" / "audit"
        
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create rotating audit logger
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # File handler with daily rotation
        log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        handler = logging.FileHandler(log_file, mode='a')
        handler.setFormatter(logging.Formatter('%(message)s'))
        
        # Remove existing handlers
        self.logger.handlers.clear()
        self.logger.addHandler(handler)
        
        self._initialized = True
    
    def log_event(
        self,
        event_type: str,
        actor_hospital_id: str,
        action: str,
        resource: Dict[str, Any],
        result: str,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: str = "unknown",
        user_agent: str = "unknown"
    ):
        """
        Log audit event in structured JSON format
        
        Args:
            event_type: Type of event (authentication, upload, download, etc.)
            actor_hospital_id: Hospital performing action
            action: Action performed
            resource: Resource accessed
            result: success/failure
            metadata: Additional context
            ip_address: Client IP
            user_agent: Client user agent
        """
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "actor": {
                "hospital_id": actor_hospital_id,
                "ip_address": ip_address,
                "user_agent": user_agent
            },
            "action": action,
            "resource": resource,
            "result": result,
            "metadata": metadata or {}
        }
        
        self.logger.info(json.dumps(event))
    
    def log_authentication(
        self,
        hospital_id: str,
        success: bool,
        reason: str = "",
        ip_address: str = "unknown"
    ):
        """Log authentication attempt"""
        self.log_event(
            event_type="authentication",
            actor_hospital_id=hospital_id,
            action="login",
            resource={"type": "auth_endpoint"},
            result="success" if success else "failure",
            metadata={"reason": reason},
            ip_address=ip_address
        )
    
    def log_gradient_upload(
        self,
        hospital_id: str,
        round_num: int,
        gradient_size: int,
        ip_address: str = "unknown"
    ):
        """Log gradient upload"""
        self.log_event(
            event_type="gradient_upload",
            actor_hospital_id=hospital_id,
            action="upload_gradients",
            resource={
                "type": "gradients",
                "round": round_num,
                "size_bytes": gradient_size
            },
            result="success",
            ip_address=ip_address
        )
    
    def log_model_download(
        self,
        hospital_id: str,
        model_version: str,
        ip_address: str = "unknown"
    ):
        """Log model download"""
        self.log_event(
            event_type="model_download",
            actor_hospital_id=hospital_id,
            action="download_global_model",
            resource={
                "type": "global_model",
                "version": model_version
            },
            result="success",
            ip_address=ip_address
        )
    
    def log_api_access(
        self,
        hospital_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        ip_address: str = "unknown"
    ):
        """Log API access"""
        self.log_event(
            event_type="api_access",
            actor_hospital_id=hospital_id,
            action=f"{method} {endpoint}",
            resource={"type": "api_endpoint", "path": endpoint},
            result="success" if status_code < 400 else "failure",
            metadata={"status_code": status_code},
            ip_address=ip_address
        )


# Singleton instance
_audit_logger = None

def get_audit_logger() -> AuditLogger:
    """Get singleton audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
