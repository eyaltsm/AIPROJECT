from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.dependencies import get_worker_user
from app.core.rate_limiting import limiter
from app.models.job import Job, JobStatus
from app.schemas.job import JobClaimResponse, JobDoneRequest, JobFailRequest
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.post("/claim", response_model=JobClaimResponse)
@limiter.limit("10/minute")
async def claim_job(
    request: Request,
    worker_data = Depends(get_worker_user),
    db: Session = Depends(get_db),
    target: str = "gpu"
):
    """Claim the next available queued job (highest priority, oldest first)."""
    # Select next available job using SKIP LOCKED to avoid contention
    job = (
        db.query(Job)
        .filter(Job.status == JobStatus.QUEUED)
        .filter(getattr(Job, "target", None) == target if hasattr(Job, "target") else True)
        .order_by(Job.priority.desc(), Job.created_at.asc())
        .with_for_update(skip_locked=True)
        .first()
    )

    if not job:
        from fastapi import Response
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    job.status = JobStatus.RUNNING
    job.reserved_by = worker_data["worker_id"]
    job.reserved_at = datetime.now(timezone.utc)
    job.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/{job_id}/done", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def mark_done(
    job_id: int,
    body: JobDoneRequest,
    worker_data = Depends(get_worker_user),
    db: Session = Depends(get_db)
):
    """Mark a job as completed by the claiming worker."""
    job = db.query(Job).get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.reserved_by != worker_data["worker_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your job")
    job.status = JobStatus.COMPLETED
    job.result_json = body.result_json
    job.error_message = None
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    return


@router.post("/jobs/{job_id}/fail", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def mark_fail(
    job_id: int,
    body: JobFailRequest,
    worker_data = Depends(get_worker_user),
    db: Session = Depends(get_db)
):
    """Mark a job as failed by the claiming worker and increment retries."""
    job = db.query(Job).get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.reserved_by != worker_data["worker_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your job")
    job.status = JobStatus.FAILED
    job.error_message = body.error_message
    job.completed_at = datetime.now(timezone.utc)
    job.retries = (job.retries or 0) + 1
    db.commit()
    return


@router.post("/claim-dryrun")
@limiter.limit("30/minute")
async def claim_dryrun(
    worker_data = Depends(get_worker_user),
    db: Session = Depends(get_db),
    target: str = "gpu"
):
    """Check if there is a job available for given target without reserving it."""
    job = (
        db.query(Job)
        .filter(Job.status == JobStatus.QUEUED)
        .filter(getattr(Job, "target", None) == target if hasattr(Job, "target") else True)
        .order_by(Job.priority.desc(), Job.created_at.asc())
        .first()
    )
    if job:
        return {"available": True, "id": job.id}
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/jobs/{job_id}/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("120/minute")
async def job_heartbeat(
    job_id: int,
    worker_data = Depends(get_worker_user),
    db: Session = Depends(get_db)
):
    """Heartbeat to keep a running job marked as active."""
    job = db.query(Job).get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.reserved_by != worker_data["worker_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your job")
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    return


@router.get("/stats")
@limiter.limit("10/minute")
async def get_worker_stats(
    worker_data = Depends(get_worker_user),
    db: Session = Depends(get_db)
):
    """Basic queue stats for observability."""
    total_queued = db.query(Job).filter(Job.status == JobStatus.QUEUED).count()
    total_running = db.query(Job).filter(Job.status == JobStatus.RUNNING).count()
    total_failed = db.query(Job).filter(Job.status == JobStatus.FAILED).count()
    total_completed = db.query(Job).filter(Job.status == JobStatus.COMPLETED).count()
    return {
        "queued": total_queued,
        "running": total_running,
        "failed": total_failed,
        "completed": total_completed,
    }


