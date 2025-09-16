from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.dataset import DatasetStatus


class DatasetBase(BaseModel):
    name: str


class DatasetCreate(DatasetBase):
    pass


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[DatasetStatus] = None


class DatasetResponse(DatasetBase):
    id: int
    user_id: int
    bucket_path: str
    image_count: int
    status: DatasetStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


