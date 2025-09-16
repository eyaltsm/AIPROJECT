from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.llm import (
    PromptGenerationRequest, PromptGenerationResponse,
    ChatCompletionRequest, ChatCompletionResponse,
    ImageAnalysisRequest, ImageAnalysisResponse,
    LLMJobPayload
)
from app.services.llm_service import llm_service, LLMProvider
from app.services.job_orchestration import JobOrchestrationService
from app.core.rate_limiting import limiter
import time
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.post("/generate-prompt", response_model=PromptGenerationResponse)
@limiter.limit("10/minute")
async def generate_prompt(
    request: Request,
    prompt_request: PromptGenerationRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a detailed prompt for image generation."""
    try:
        start_time = time.time()
        
        result = await llm_service.generate_prompt(
            user_input=prompt_request.user_input,
            style=prompt_request.style,
            provider=prompt_request.provider
        )
        
        processing_time = time.time() - start_time
        
        # Extract the generated prompt from the response
        if prompt_request.provider == LLMProvider.OPENAI:
            prompt = result["choices"][0]["message"]["content"]
            tokens_used = result["usage"]["total_tokens"]
        elif prompt_request.provider == LLMProvider.ANTHROPIC:
            prompt = result["content"][0]["text"]
            tokens_used = result["usage"]["input_tokens"] + result["usage"]["output_tokens"]
        else:
            prompt = result["choices"][0]["message"]["content"]
            tokens_used = result.get("usage", {}).get("total_tokens", 0)
        
        logger.info(
            "Prompt generated successfully",
            user_id=current_user.id,
            provider=prompt_request.provider,
            tokens_used=tokens_used,
            processing_time=processing_time
        )
        
        return PromptGenerationResponse(
            prompt=prompt,
            provider=prompt_request.provider.value,
            tokens_used=tokens_used,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error("Prompt generation failed", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate prompt")


@router.post("/chat", response_model=ChatCompletionResponse)
@limiter.limit("20/minute")
async def chat_completion(
    request: Request,
    chat_request: ChatCompletionRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handle chat completion requests."""
    try:
        start_time = time.time()
        
        # Convert Pydantic messages to dict format
        messages = [{"role": msg.role, "content": msg.content} for msg in chat_request.messages]
        
        result = await llm_service.chat_completion(
            messages=messages,
            provider=chat_request.provider
        )
        
        processing_time = time.time() - start_time
        
        # Extract response based on provider
        if chat_request.provider == LLMProvider.OPENAI:
            message = result["choices"][0]["message"]["content"]
            tokens_used = result["usage"]["total_tokens"]
        elif chat_request.provider == LLMProvider.ANTHROPIC:
            message = result["content"][0]["text"]
            tokens_used = result["usage"]["input_tokens"] + result["usage"]["output_tokens"]
        else:
            message = result["choices"][0]["message"]["content"]
            tokens_used = result.get("usage", {}).get("total_tokens", 0)
        
        logger.info(
            "Chat completion successful",
            user_id=current_user.id,
            provider=chat_request.provider,
            tokens_used=tokens_used,
            processing_time=processing_time
        )
        
        return ChatCompletionResponse(
            message=message,
            provider=chat_request.provider.value if chat_request.provider else "openai",
            tokens_used=tokens_used,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error("Chat completion failed", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to complete chat")


@router.post("/analyze-image", response_model=ImageAnalysisResponse)
@limiter.limit("5/minute")
async def analyze_image(
    request: Request,
    analysis_request: ImageAnalysisRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze an image using vision models."""
    try:
        start_time = time.time()
        
        result = await llm_service.analyze_image(
            image_url=analysis_request.image_url,
            analysis_type=analysis_request.analysis_type,
            provider=analysis_request.provider
        )
        
        processing_time = time.time() - start_time
        
        # Extract analysis based on provider
        if analysis_request.provider == LLMProvider.OPENAI:
            analysis = result["choices"][0]["message"]["content"]
            tokens_used = result["usage"]["total_tokens"]
        elif analysis_request.provider == LLMProvider.ANTHROPIC:
            analysis = result["content"][0]["text"]
            tokens_used = result["usage"]["input_tokens"] + result["usage"]["output_tokens"]
        else:
            analysis = result["choices"][0]["message"]["content"]
            tokens_used = result.get("usage", {}).get("total_tokens", 0)
        
        logger.info(
            "Image analysis successful",
            user_id=current_user.id,
            analysis_type=analysis_request.analysis_type,
            provider=analysis_request.provider,
            tokens_used=tokens_used,
            processing_time=processing_time
        )
        
        return ImageAnalysisResponse(
            analysis=analysis,
            analysis_type=analysis_request.analysis_type,
            provider=analysis_request.provider.value if analysis_request.provider else "openai",
            tokens_used=tokens_used,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error("Image analysis failed", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to analyze image")


@router.post("/queue-prompt-job")
@limiter.limit("5/minute")
async def queue_prompt_job(
    request: Request,
    job_payload: LLMJobPayload,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Queue an LLM job for background processing."""
    try:
        job_service = JobOrchestrationService(db)
        
        # Create job payload
        job_data = {
            "provider": job_payload.provider.value,
            "request_type": job_payload.request_type,
            "request_data": job_payload.request_data,
            "user_id": current_user.id,
            "priority": job_payload.priority
        }
        
        # TODO: Create job in database
        # job = job_service.create_job(
        #     user_id=current_user.id,
        #     kind=JobKind.GENERATE_PROMPT,  # or other LLM job types
        #     payload_json=job_data
        # )
        
        logger.info(
            "LLM job queued",
            user_id=current_user.id,
            job_type=job_payload.request_type,
            provider=job_payload.provider
        )
        
        return {"message": "Job queued successfully", "job_id": "placeholder"}
        
    except Exception as e:
        logger.error("Failed to queue LLM job", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to queue job")


@router.get("/providers")
@limiter.limit("60/minute")
async def list_providers(request: Request):
    """List available LLM providers."""
    return {
        "providers": [
            {"id": "openai", "name": "OpenAI", "models": ["gpt-4o-mini", "gpt-4o"]},
            {"id": "anthropic", "name": "Anthropic", "models": ["claude-3-haiku", "claude-3-sonnet"]},
            {"id": "groq", "name": "Groq", "models": ["llama-3.1-70b", "mixtral-8x7b"]},
            {"id": "together", "name": "Together AI", "models": ["llama-3.1-70b", "qwen-2.5-72b"]}
        ]
    }


