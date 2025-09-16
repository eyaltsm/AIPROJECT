from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CreditResponse(BaseModel):
    user_id: int
    images_remaining: int = Field(..., ge=0)
    videos_remaining: int = Field(..., ge=0)
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class CreditUpdate(BaseModel):
    images_remaining: Optional[int] = Field(None, ge=0)
    videos_remaining: Optional[int] = Field(None, ge=0)
