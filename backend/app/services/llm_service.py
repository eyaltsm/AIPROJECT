from typing import Dict, Any, Optional, List
from enum import Enum
import httpx
import structlog
from app.core.config import settings

logger = structlog.get_logger()


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    TOGETHER = "together"


class LLMService:
    """Service for LLM API integration with multiple providers."""
    
    def __init__(self):
        self.providers = {
            LLMProvider.OPENAI: self._call_openai,
            LLMProvider.ANTHROPIC: self._call_anthropic,
            LLMProvider.GROQ: self._call_groq,
            LLMProvider.TOGETHER: self._call_together,
        }
    
    async def generate_prompt(
        self,
        user_input: str,
        style: str = "photorealistic",
        provider: Optional[LLMProvider] = None
    ) -> Dict[str, Any]:
        """Generate a detailed prompt for image generation."""
        system_prompt = f"""You are an expert prompt engineer for AI image generation. 
        Create detailed, high-quality prompts for Stable Diffusion XL that will generate {style} images.
        
        Guidelines:
        - Use specific, descriptive language
        - Include technical photography terms (aperture, lighting, composition)
        - Mention art style, mood, and atmosphere
        - Keep prompts under 200 words
        - Avoid banned terms or inappropriate content
        - Focus on visual details that will improve image quality
        
        User request: {user_input}"""
        
        return await self._call_llm(
            system_prompt=system_prompt,
            user_message=f"Create a detailed prompt for: {user_input}",
            provider=provider
        )
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        provider: Optional[LLMProvider] = None
    ) -> Dict[str, Any]:
        """Handle chat completion requests."""
        return await self._call_llm(
            messages=messages,
            provider=provider
        )
    
    async def analyze_image(
        self,
        image_url: str,
        analysis_type: str = "describe",
        provider: Optional[LLMProvider] = None
    ) -> Dict[str, Any]:
        """Analyze an image using vision models."""
        if analysis_type == "describe":
            prompt = "Describe this image in detail, focusing on visual elements, composition, style, and mood."
        elif analysis_type == "nsfw_check":
            prompt = "Analyze this image for NSFW content. Respond with 'safe' or 'nsfw' and a brief explanation."
        elif analysis_type == "style_analysis":
            prompt = "Analyze the artistic style, technique, and visual characteristics of this image."
        else:
            prompt = f"Analyze this image: {analysis_type}"
        
        return await self._call_llm(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }],
            provider=provider
        )
    
    async def _call_llm(
        self,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        provider: Optional[LLMProvider] = None
    ) -> Dict[str, Any]:
        """Call LLM with the specified provider."""
        if not provider:
            provider = LLMProvider(settings.DEFAULT_LLM_PROVIDER)
        
        if provider not in self.providers:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        
        try:
            return await self.providers[provider](
                system_prompt=system_prompt,
                user_message=user_message,
                messages=messages
            )
        except Exception as e:
            logger.error("LLM API call failed", provider=provider, error=str(e))
            raise
    
    async def _call_openai(
        self,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Call OpenAI API."""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        
        if not messages:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if user_message:
                messages.append({"role": "user", "content": user_message})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "max_tokens": settings.LLM_MAX_TOKENS,
                    "temperature": settings.LLM_TEMPERATURE
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def _call_anthropic(
        self,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Call Anthropic Claude API."""
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("Anthropic API key not configured")
        
        if not messages:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if user_message:
                messages.append({"role": "user", "content": user_message})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": settings.LLM_MAX_TOKENS,
                    "temperature": settings.LLM_TEMPERATURE,
                    "messages": messages
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def _call_groq(
        self,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Call Groq API."""
        if not settings.GROQ_API_KEY:
            raise ValueError("Groq API key not configured")
        
        if not messages:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if user_message:
                messages.append({"role": "user", "content": user_message})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-70b-versatile",
                    "messages": messages,
                    "max_tokens": settings.LLM_MAX_TOKENS,
                    "temperature": settings.LLM_TEMPERATURE
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def _call_together(
        self,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Call Together AI API."""
        if not settings.TOGETHER_API_KEY:
            raise ValueError("Together AI API key not configured")
        
        if not messages:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if user_message:
                messages.append({"role": "user", "content": user_message})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.TOGETHER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "meta-llama/Llama-3.1-70B-Instruct-Turbo",
                    "messages": messages,
                    "max_tokens": settings.LLM_MAX_TOKENS,
                    "temperature": settings.LLM_TEMPERATURE
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()


# Global LLM service instance
llm_service = LLMService()


