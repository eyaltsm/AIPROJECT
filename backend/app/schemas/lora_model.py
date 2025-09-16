from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.lora_model import LoRAStatus


class LoRAModelBase(BaseModel):
    name: str
    rank: int = 16
    steps: int = 1000


class LoRAModelCreate(LoRAModelBase):
    dataset_id: int


class LoRAModelUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[LoRAStatus] = None
    model_hash: Optional[str] = None
    training_config: Optional[str] = None


class LoRAModelResponse(LoRAModelBase):
    id: int
    user_id: int
    dataset_id: int
    bucket_path: str
    status: LoRAStatus
    model_hash: Optional[str] = None
    training_config: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


