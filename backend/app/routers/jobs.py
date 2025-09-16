from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.job import JobResponse, JobCreate, JobUpdate
from app.services.vast_service import ensure_gpu_instance
from app.core.rate_limiting import limiter
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("/", response_model=list[JobResponse])
@limiter.limit("30/minute")
async def list_jobs(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's jobs."""
    # TODO: Implement job listing
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/", response_model=JobResponse)
@limiter.limit("5/minute")
async def create_job(
    job: JobCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new job."""
    # TODO: Implement: persist job in DB. For now only trigger GPU autoscale.
    try:
        # Fire-and-forget ensure GPU for gpu-target jobs
        payload = job.payload_json or {}
        target = payload.get("target") or payload.get("worker_target") or "local"
        if target == "gpu":
            ensure_gpu_instance()
        # Not implementing full persistence here per scope
        raise HTTPException(status_code=501, detail="Job creation persistence not implemented in this stub")
    except Exception as e:
        logger.error("job_create_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create job")


@router.get("/{job_id}", response_model=JobResponse)
@limiter.limit("60/minute")
async def get_job(
    job_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get job by ID."""
    # TODO: Implement job retrieval
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch("/{job_id}", response_model=JobResponse)
@limiter.limit("10/minute")
async def update_job(
    job_id: int,
    job_update: JobUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update job."""
    # TODO: Implement job update
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/{job_id}")
@limiter.limit("5/minute")
async def cancel_job(
    job_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel job."""
    # TODO: Implement job cancellation
    raise HTTPException(status_code=501, detail="Not implemented")


