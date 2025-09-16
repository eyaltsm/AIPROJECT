from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.output import OutputType


class OutputResponse(BaseModel):
    id: int
    user_id: int
    job_id: int
    lora_id: Optional[int] = None
    type: OutputType
    object_key: str = Field(..., max_length=512)
    prompt_hash: str = Field(..., max_length=32)
    seed: str = Field(..., max_length=50)
    model_hash: str = Field(..., max_length=64)
    output_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}
