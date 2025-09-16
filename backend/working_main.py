#!/usr/bin/env python3
"""
Working FastAPI app with job queue system for AI Generation Platform.
"""

from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import structlog
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime

from app.core.config import settings
from app.core.database import engine, Base, get_db
from app.core.security import create_access_token, create_worker_token
from app.models.job import Job, JobKind, JobStatus
from app.models.user import User
from app.schemas.job import JobCreate, JobResponse, JobClaimResponse

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting AI Generation Platform", version=settings.VERSION)
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Generation Platform")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="A secure and scalable AI image/video generation platform.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # Add request ID to request state
    request.state.request_id = request_id

    # Log request details
    logger.info(
        "Request started",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host,
    )

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=f"{process_time:.4f}s",
        client_ip=request.client.host,
    )
    return response

# Health check endpoint
@app.get("/api/health", tags=["Monitoring"])
async def health_check(request: Request):
    return {
        "status": "ok",
        "version": settings.VERSION,
        "request_id": request.state.request_id,
        "timestamp": time.time(),
        "message": "AI Generation Platform is running!"
    }

# Test database connection
@app.get("/api/test-db", tags=["Testing"])
async def test_database(db: Session = Depends(get_db)):
    try:
        # Test database connection
        from sqlalchemy import text
        result = db.execute(text("SELECT 1 as test"))
        test_value = result.fetchone()[0]
        
        return {
            "status": "ok",
            "database": "connected",
            "test_value": test_value
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "failed",
            "error": str(e)
        }

# Job endpoints
@app.post("/api/jobs", response_model=JobResponse, tags=["Jobs"])
async def create_job(
    job_data: JobCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new job."""
    try:
        # For now, create a dummy user if none exists
        user = db.query(User).first()
        if not user:
            # Create a test user
            user = User(
                email="test@example.com",
                supabase_user_id="test-user-123"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Create job
        job = Job(
            user_id=user.id,
            kind=job_data.kind,
            payload_json=job_data.payload_json,
            status=JobStatus.QUEUED,
            priority=job_data.priority or 0
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(
            "Job created",
            job_id=job.id,
            kind=job.kind,
            user_id=user.id,
            request_id=request.state.request_id
        )
        
        return JobResponse.from_orm(job)
        
    except Exception as e:
        logger.error("Failed to create job", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job"
        )

@app.get("/api/jobs/{job_id}", response_model=JobResponse, tags=["Jobs"])
async def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get job status."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return JobResponse.from_orm(job)

# Worker endpoints
@app.post("/api/workers/claim", response_model=JobClaimResponse, tags=["Workers"])
async def claim_job(
    request: Request,
    db: Session = Depends(get_db)
):
    """Claim a job for processing (worker endpoint)."""
    try:
        # For now, just return a test job
        # In production, this would use atomic claiming with FOR UPDATE SKIP LOCKED
        
        job = db.query(Job).filter(Job.status == JobStatus.QUEUED).first()
        if not job:
            return JSONResponse(status_code=204, content=None)
        
        # Update job status
        job.status = JobStatus.RUNNING
        job.reserved_by = request.headers.get("X-Worker-Id", "unknown")
        job.reserved_at = datetime.utcnow()
        db.commit()
        
        logger.info(
            "Job claimed",
            job_id=job.id,
            worker_id=job.reserved_by,
            request_id=request.state.request_id
        )
        
        return JobClaimResponse.from_orm(job)
        
    except Exception as e:
        logger.error("Failed to claim job", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to claim job"
        )

@app.post("/api/workers/jobs/{job_id}/done", tags=["Workers"])
async def mark_job_done(
    job_id: int,
    result: dict,
    request: Request,
    db: Session = Depends(get_db)
):
    """Mark job as completed (worker endpoint)."""
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        job.status = JobStatus.COMPLETED
        job.result_json = result
        job.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(
            "Job completed",
            job_id=job.id,
            result=result,
            request_id=request.state.request_id
        )
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error("Failed to mark job done", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark job done"
        )

@app.post("/api/workers/jobs/{job_id}/fail", tags=["Workers"])
async def mark_job_failed(
    job_id: int,
    error_data: dict,
    request: Request,
    db: Session = Depends(get_db)
):
    """Mark job as failed (worker endpoint)."""
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        job.status = JobStatus.FAILED
        job.error_message = error_data.get("error", "Unknown error")
        job.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(
            "Job failed",
            job_id=job.id,
            error=error_data.get("error"),
            request_id=request.state.request_id
        )
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error("Failed to mark job failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark job failed"
        )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled exception",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
