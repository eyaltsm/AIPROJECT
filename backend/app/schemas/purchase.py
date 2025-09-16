from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.models.purchase import PurchaseStatus


class PurchaseCreate(BaseModel):
    bundle_id: int = Field(..., gt=0)


class PurchaseResponse(BaseModel):
    id: int
    user_id: int
    bundle_id: int
    stripe_payment_id: Optional[str] = None
    amount_usd: Decimal = Field(..., ge=Decimal("0"))
    status: PurchaseStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}
