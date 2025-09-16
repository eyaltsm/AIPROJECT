from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.services.llm_service import LLMProvider


class PromptGenerationRequest(BaseModel):
    user_input: str = Field(..., min_length=1, max_length=500)
    style: str = Field(default="photorealistic", max_length=100)
    provider: Optional[LLMProvider] = None


class PromptGenerationResponse(BaseModel):
    prompt: str
    provider: str
    tokens_used: int
    processing_time: float


class ChatMessage(BaseModel):
    role: str = Field(..., regex="^(system|user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4000)


class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_items=1, max_items=20)
    provider: Optional[LLMProvider] = None
    max_tokens: Optional[int] = Field(None, ge=1, le=4000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)


class ChatCompletionResponse(BaseModel):
    message: str
    provider: str
    tokens_used: int
    processing_time: float


class ImageAnalysisRequest(BaseModel):
    image_url: str = Field(..., max_length=1000)
    analysis_type: str = Field(default="describe", regex="^(describe|nsfw_check|style_analysis)$")
    provider: Optional[LLMProvider] = None


class ImageAnalysisResponse(BaseModel):
    analysis: str
    analysis_type: str
    provider: str
    tokens_used: int
    processing_time: float


class LLMJobPayload(BaseModel):
    """Payload for LLM jobs in the queue system."""
    provider: LLMProvider
    request_type: str = Field(..., regex="^(prompt_generation|chat_completion|image_analysis)$")
    request_data: Dict[str, Any]
    user_id: int
    priority: int = Field(default=0, ge=0, le=10)


