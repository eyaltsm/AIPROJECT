from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.audit_log import AuditLog
from app.models.user import User
import structlog

logger = structlog.get_logger()


class AuditService:
    """Service for audit logging and compliance."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_action(
        self,
        action: str,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        meta_data: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log an audit action."""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                meta_json=meta_data,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.utcnow()
            )
            
            self.db.add(audit_log)
            self.db.commit()
            
            logger.info(
                "Audit log created",
                action=action,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id
            )
            
            return audit_log
            
        except Exception as e:
            logger.error("Error creating audit log", action=action, error=str(e))
            self.db.rollback()
            raise
    
    def log_user_action(
        self,
        action: str,
        user: User,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        meta_data: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log a user action with user context."""
        return self.log_action(
            action=action,
            user_id=user.id,
            resource_type=resource_type,
            resource_id=resource_id,
            meta_data=meta_data,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_job_transition(
        self,
        job_id: int,
        old_status: str,
        new_status: str,
        user_id: Optional[int] = None,
        worker_id: Optional[str] = None,
        meta_data: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Log job status transition."""
        return self.log_action(
            action="job_status_change",
            user_id=user_id,
            resource_type="job",
            resource_id=str(job_id),
            meta_data={
                "old_status": old_status,
                "new_status": new_status,
                "worker_id": worker_id,
                **(meta_data or {})
            }
        )
    
    def log_purchase(
        self,
        purchase_id: int,
        user_id: int,
        amount: float,
        status: str,
        payment_method: str,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log purchase transaction."""
        return self.log_action(
            action="purchase_created",
            user_id=user_id,
            resource_type="purchase",
            resource_id=str(purchase_id),
            meta_data={
                "amount": amount,
                "status": status,
                "payment_method": payment_method
            },
            ip_address=ip_address
        )
    
    def log_token_issue(
        self,
        user_id: int,
        token_type: str,
        scopes: list[str],
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log token issuance."""
        return self.log_action(
            action="token_issued",
            user_id=user_id,
            resource_type="token",
            meta_data={
                "token_type": token_type,
                "scopes": scopes
            },
            ip_address=ip_address
        )
    
    def log_token_revoke(
        self,
        user_id: int,
        token_type: str,
        reason: str,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log token revocation."""
        return self.log_action(
            action="token_revoked",
            user_id=user_id,
            resource_type="token",
            meta_data={
                "token_type": token_type,
                "reason": reason
            },
            ip_address=ip_address
        )
    
    def log_file_upload(
        self,
        user_id: int,
        file_type: str,
        file_size: int,
        dataset_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log file upload."""
        return self.log_action(
            action="file_uploaded",
            user_id=user_id,
            resource_type="file",
            resource_id=str(dataset_id) if dataset_id else None,
            meta_data={
                "file_type": file_type,
                "file_size": file_size,
                "dataset_id": dataset_id
            },
            ip_address=ip_address
        )
    
    def log_generation(
        self,
        user_id: int,
        output_id: int,
        prompt_hash: str,
        model_hash: str,
        lora_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log content generation."""
        return self.log_action(
            action="content_generated",
            user_id=user_id,
            resource_type="output",
            resource_id=str(output_id),
            meta_data={
                "prompt_hash": prompt_hash,
                "model_hash": model_hash,
                "lora_id": lora_id
            },
            ip_address=ip_address
        )


