from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.models.job import Job, JobStatus, JobKind
from app.core.database import get_db
import structlog

logger = structlog.get_logger()


class JobOrchestrationService:
    """Service for managing job queue and worker coordination."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def claim_job(self, worker_id: str, job_kinds: list[JobKind] = None) -> Optional[Job]:
        """Atomically claim a job for processing."""
        try:
            # Build the query for job claiming
            query = """
                UPDATE jobs 
                SET status = 'running', 
                    reserved_by = :worker_id, 
                    reserved_at = :now,
                    started_at = :now,
                    updated_at = :now
                WHERE id = (
                    SELECT id FROM jobs
                    WHERE status = 'queued'
                    AND (:job_kinds IS NULL OR kind = ANY(:job_kinds))
                    ORDER BY priority DESC, created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING *;
            """
            
            result = self.db.execute(
                text(query),
                {
                    "worker_id": worker_id,
                    "now": datetime.utcnow(),
                    "job_kinds": job_kinds or [kind.value for kind in JobKind]
                }
            ).fetchone()
            
            if result:
                # Convert result to Job object
                job = self.db.query(Job).filter(Job.id == result.id).first()
                logger.info(
                    "Job claimed successfully",
                    job_id=job.id,
                    worker_id=worker_id,
                    job_kind=job.kind
                )
                return job
            
            return None
            
        except Exception as e:
            logger.error("Error claiming job", worker_id=worker_id, error=str(e))
            self.db.rollback()
            return None
    
    def update_job_status(
        self, 
        job_id: int, 
        status: JobStatus, 
        worker_id: str,
        result_data: Dict[str, Any] = None,
        error_message: str = None
    ) -> bool:
        """Update job status with validation."""
        try:
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if not job:
                logger.error("Job not found", job_id=job_id)
                return False
            
            # Validate worker can update this job
            if job.reserved_by != worker_id:
                logger.error(
                    "Worker not authorized to update job",
                    job_id=job_id,
                    worker_id=worker_id,
                    reserved_by=job.reserved_by
                )
                return False
            
            # Validate status transition
            if not self._is_valid_status_transition(job.status, status):
                logger.error(
                    "Invalid status transition",
                    job_id=job_id,
                    current_status=job.status,
                    new_status=status
                )
                return False
            
            # Update job
            job.status = status
            job.updated_at = datetime.utcnow()
            
            if status == JobStatus.COMPLETED:
                job.completed_at = datetime.utcnow()
                if result_data:
                    job.result_json = result_data
            elif status == JobStatus.FAILED:
                job.completed_at = datetime.utcnow()
                if error_message:
                    job.error_message = error_message
                # Increment retries
                job.retries += 1
                
                # If retries exceeded, mark as failed permanently
                if job.retries >= 3:
                    job.status = JobStatus.FAILED
                else:
                    # Reset to queued for retry
                    job.status = JobStatus.QUEUED
                    job.reserved_by = None
                    job.reserved_at = None
            
            self.db.commit()
            
            logger.info(
                "Job status updated",
                job_id=job_id,
                old_status=job.status,
                new_status=status,
                worker_id=worker_id
            )
            
            return True
            
        except Exception as e:
            logger.error("Error updating job status", job_id=job_id, error=str(e))
            self.db.rollback()
            return False
    
    def _is_valid_status_transition(self, current: JobStatus, new: JobStatus) -> bool:
        """Validate if status transition is allowed."""
        valid_transitions = {
            JobStatus.QUEUED: [JobStatus.RUNNING, JobStatus.CANCELLED],
            JobStatus.RUNNING: [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED],
            JobStatus.COMPLETED: [],  # Terminal state
            JobStatus.FAILED: [JobStatus.QUEUED],  # Can retry
            JobStatus.CANCELLED: []  # Terminal state
        }
        
        return new in valid_transitions.get(current, [])
    
    def requeue_stuck_jobs(self, timeout_minutes: int = 30) -> int:
        """Requeue jobs that have been running too long without heartbeat."""
        try:
            timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
            
            # Find stuck jobs
            stuck_jobs = self.db.query(Job).filter(
                Job.status == JobStatus.RUNNING,
                Job.reserved_at < timeout_threshold
            ).all()
            
            count = 0
            for job in stuck_jobs:
                job.status = JobStatus.QUEUED
                job.reserved_by = None
                job.reserved_at = None
                job.retries += 1
                job.updated_at = datetime.utcnow()
                
                # If too many retries, mark as failed
                if job.retries >= 3:
                    job.status = JobStatus.FAILED
                    job.completed_at = datetime.utcnow()
                    job.error_message = "Job timed out after multiple retries"
                
                count += 1
            
            self.db.commit()
            
            if count > 0:
                logger.info("Requeued stuck jobs", count=count)
            
            return count
            
        except Exception as e:
            logger.error("Error requeuing stuck jobs", error=str(e))
            self.db.rollback()
            return 0
    
    def get_job_stats(self) -> Dict[str, int]:
        """Get job queue statistics."""
        try:
            stats = {}
            for status in JobStatus:
                count = self.db.query(Job).filter(Job.status == status).count()
                stats[status.value] = count
            
            return stats
            
        except Exception as e:
            logger.error("Error getting job stats", error=str(e))
            return {}


