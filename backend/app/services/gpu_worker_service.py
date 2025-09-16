from typing import Dict, Any, Optional, List
from enum import Enum
import httpx
import structlog
from app.core.config import settings

logger = structlog.get_logger()


class GPUProvider(str, Enum):
    VAST_AI = "vast_ai"
    RUNPOD = "runpod"
    LAMBDA_LABS = "lambda_labs"


class GPUWorkerService:
    """Service for managing GPU workers and diffusion model jobs."""
    
    def __init__(self):
        self.providers = {
            GPUProvider.VAST_AI: self._call_vast_ai,
            GPUProvider.RUNPOD: self._call_runpod,
            GPUProvider.LAMBDA_LABS: self._call_lambda_labs,
        }
    
    async def start_worker(
        self,
        job_type: str,
        provider: GPUProvider = GPUProvider.VAST_AI,
        gpu_type: str = "RTX 4090",
        max_price: float = 0.5
    ) -> Dict[str, Any]:
        """Start a GPU worker for processing jobs."""
        try:
            if provider == GPUProvider.VAST_AI:
                return await self._start_vast_ai_worker(job_type, gpu_type, max_price)
            elif provider == GPUProvider.RUNPOD:
                return await self._start_runpod_worker(job_type, gpu_type, max_price)
            else:
                raise ValueError(f"Unsupported GPU provider: {provider}")
                
        except Exception as e:
            logger.error("Failed to start GPU worker", provider=provider, error=str(e))
            raise
    
    async def stop_worker(self, worker_id: str, provider: GPUProvider) -> bool:
        """Stop a GPU worker."""
        try:
            if provider == GPUProvider.VAST_AI:
                return await self._stop_vast_ai_worker(worker_id)
            elif provider == GPUProvider.RUNPOD:
                return await self._stop_runpod_worker(worker_id)
            else:
                raise ValueError(f"Unsupported GPU provider: {provider}")
                
        except Exception as e:
            logger.error("Failed to stop GPU worker", worker_id=worker_id, error=str(e))
            return False
    
    async def get_worker_status(self, worker_id: str, provider: GPUProvider) -> Dict[str, Any]:
        """Get worker status and metrics."""
        try:
            if provider == GPUProvider.VAST_AI:
                return await self._get_vast_ai_worker_status(worker_id)
            elif provider == GPUProvider.RUNPOD:
                return await self._get_runpod_worker_status(worker_id)
            else:
                raise ValueError(f"Unsupported GPU provider: {provider}")
                
        except Exception as e:
            logger.error("Failed to get worker status", worker_id=worker_id, error=str(e))
            return {"status": "error", "error": str(e)}
    
    async def _start_vast_ai_worker(
        self, 
        job_type: str, 
        gpu_type: str, 
        max_price: float
    ) -> Dict[str, Any]:
        """Start a Vast.ai worker."""
        if not settings.VAST_AI_API_KEY:
            raise ValueError("Vast.ai API key not configured")
        
        # Create worker startup script based on job type
        startup_script = self._generate_startup_script(job_type)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://console.vast.ai/api/v0/asks/",
                headers={"Authorization": f"Bearer {settings.VAST_AI_API_KEY}"},
                json={
                    "client_id": "me",
                    "image": "pytorch/pytorch:latest",
                    "disk": 20,
                    "gpu_name": gpu_type,
                    "max_price": max_price,
                    "onstart": startup_script,
                    "env": {
                        "API_BASE_URL": settings.API_BASE_URL,
                        "WORKER_TOKEN": "placeholder"  # Will be set by worker
                    }
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def _start_runpod_worker(
        self, 
        job_type: str, 
        gpu_type: str, 
        max_price: float
    ) -> Dict[str, Any]:
        """Start a RunPod worker."""
        if not settings.RUNPOD_API_KEY:
            raise ValueError("RunPod API key not configured")
        
        # Map job type to RunPod template
        template_id = self._get_runpod_template(job_type)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.runpod.io/v2/run",
                headers={"Authorization": f"Bearer {settings.RUNPOD_API_KEY}"},
                json={
                    "templateId": template_id,
                    "input": {
                        "job_type": job_type,
                        "api_base_url": settings.API_BASE_URL
                    }
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def _stop_vast_ai_worker(self, worker_id: str) -> bool:
        """Stop a Vast.ai worker."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://console.vast.ai/api/v0/asks/{worker_id}/",
                headers={"Authorization": f"Bearer {settings.VAST_AI_API_KEY}"},
                timeout=30.0
            )
            return response.status_code == 200
    
    async def _stop_runpod_worker(self, worker_id: str) -> bool:
        """Stop a RunPod worker."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.runpod.io/v2/{worker_id}/stop",
                headers={"Authorization": f"Bearer {settings.RUNPOD_API_KEY}"},
                timeout=30.0
            )
            return response.status_code == 200
    
    async def _get_vast_ai_worker_status(self, worker_id: str) -> Dict[str, Any]:
        """Get Vast.ai worker status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://console.vast.ai/api/v0/asks/{worker_id}/",
                headers={"Authorization": f"Bearer {settings.VAST_AI_API_KEY}"},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def _get_runpod_worker_status(self, worker_id: str) -> Dict[str, Any]:
        """Get RunPod worker status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.runpod.io/v2/{worker_id}/status",
                headers={"Authorization": f"Bearer {settings.RUNPOD_API_KEY}"},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    def _generate_startup_script(self, job_type: str) -> str:
        """Generate startup script for GPU worker."""
        if job_type == "train_lora":
            return """
#!/bin/bash
# Install dependencies
pip install diffusers transformers accelerate
pip install kohya-ss
pip install requests

# Download and setup ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt

# Start worker
python worker.py --job-type train_lora --api-url $API_BASE_URL --token $WORKER_TOKEN
"""
        elif job_type == "generate_image":
            return """
#!/bin/bash
# Install dependencies
pip install diffusers transformers accelerate
pip install requests

# Download and setup ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt

# Start worker
python worker.py --job-type generate_image --api-url $API_BASE_URL --token $WORKER_TOKEN
"""
        elif job_type == "generate_video":
            return """
#!/bin/bash
# Install dependencies
pip install diffusers transformers accelerate
pip install animatediff
pip install requests

# Download and setup ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt

# Start worker
python worker.py --job-type generate_video --api-url $API_BASE_URL --token $WORKER_TOKEN
"""
        else:
            return """
#!/bin/bash
# Generic worker setup
pip install requests

# Start worker
python worker.py --api-url $API_BASE_URL --token $WORKER_TOKEN
"""
    
    def _get_runpod_template(self, job_type: str) -> str:
        """Get RunPod template ID for job type."""
        templates = {
            "train_lora": "sd-lora-training",
            "generate_image": "sd-inference",
            "generate_video": "animatediff-inference"
        }
        return templates.get(job_type, "generic-ai-worker")


# Global GPU worker service instance
gpu_worker_service = GPUWorkerService()


