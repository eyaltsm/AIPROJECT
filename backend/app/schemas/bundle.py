from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class BundleBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    credits_images: int = Field(0, ge=0)
    credits_video: int = Field(0, ge=0)
    price_usd: Decimal = Field(..., ge=Decimal("0"))


class BundleCreate(BundleBase):
    pass


class BundleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    credits_images: Optional[int] = Field(None, ge=0)
    credits_video: Optional[int] = Field(None, ge=0)
    price_usd: Optional[Decimal] = Field(None, ge=Decimal("0"))
    is_active: Optional[bool] = None


class BundleResponse(BundleBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}
