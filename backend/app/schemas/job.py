"""
Pydantic schemas for job-related requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from app.models.job import JobKind, JobStatus

class JobCreate(BaseModel):
    """Schema for creating a new job."""
    kind: JobKind
    payload_json: Dict[str, Any]
    priority: Optional[int] = Field(default=0, ge=0, le=10)

class JobResponse(BaseModel):
    """Schema for job response."""
    id: int
    user_id: int
    kind: JobKind
    status: JobStatus
    priority: int
    payload_json: Dict[str, Any]
    result_json: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    reserved_by: Optional[str] = None
    reserved_at: Optional[datetime] = None
    retries: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class JobClaimResponse(BaseModel):
    """Schema for job claim response."""
    id: int
    user_id: int
    kind: JobKind
    status: JobStatus
    priority: int
    payload_json: Dict[str, Any]
    reserved_by: Optional[str] = None
    reserved_at: Optional[datetime] = None
    retries: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class JobUpdate(BaseModel):
    """Schema for updating a job."""
    status: Optional[JobStatus] = None
    result_json: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retries: Optional[int] = None


class JobDoneRequest(BaseModel):
    """Schema sent by worker when job completes successfully."""
    result_json: Dict[str, Any]


class JobFailRequest(BaseModel):
    """Schema sent by worker when job fails."""
    error_message: str