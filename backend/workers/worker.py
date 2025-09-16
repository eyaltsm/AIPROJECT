#!/usr/bin/env python3
"""
GPU Worker for AI Generation Platform
Handles diffusion model inference and LoRA training
"""

import asyncio
import argparse
import json
import time
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import aiohttp
import torch
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline
from PIL import Image
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class GPUWorker:
    """GPU worker for processing AI generation jobs."""
    
    def __init__(self, api_url: str, worker_token: str, worker_id: str = None):
        self.api_url = api_url
        self.worker_token = worker_token
        self.worker_id = worker_id or f"worker-{os.getpid()}"
        self.session = None
        
        # Model cache
        self.models = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info("GPU Worker initialized", worker_id=self.worker_id, device=self.device)
    
    async def start(self):
        """Start the worker main loop."""
        logger.info("Starting GPU worker", worker_id=self.worker_id)
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            while True:
                try:
                    # Claim a job
                    job = await self.claim_job()
                    if job:
                        await self.process_job(job)
                    else:
                        # No jobs available, wait
                        await asyncio.sleep(5)
                        
                except Exception as e:
                    logger.error("Worker error", error=str(e), exc_info=True)
                    await asyncio.sleep(10)
    
    async def claim_job(self) -> Optional[Dict[str, Any]]:
        """Claim a job from the API."""
        try:
            async with self.session.post(
                f"{self.api_url}/api/v1/workers/claim",
                headers={"Authorization": f"Bearer {self.worker_token}"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    job_data = await response.json()
                    logger.info("Job claimed", job_id=job_data.get("id"))
                    return job_data
                elif response.status == 404:
                    # No jobs available
                    return None
                else:
                    logger.error("Failed to claim job", status=response.status)
                    return None
                    
        except Exception as e:
            logger.error("Error claiming job", error=str(e))
            return None
    
    async def process_job(self, job: Dict[str, Any]):
        """Process a claimed job."""
        job_id = job["id"]
        job_kind = job["kind"]
        payload = job["payload_json"]
        
        logger.info("Processing job", job_id=job_id, kind=job_kind)
        
        try:
            if job_kind == "generate_image":
                result = await self.generate_image(payload)
            elif job_kind == "generate_video":
                result = await self.generate_video(payload)
            elif job_kind == "train_lora":
                result = await self.train_lora(payload)
            else:
                raise ValueError(f"Unknown job kind: {job_kind}")
            
            # Update job as completed
            await self.update_job_status(job_id, "completed", result)
            logger.info("Job completed successfully", job_id=job_id)
            
        except Exception as e:
            logger.error("Job failed", job_id=job_id, error=str(e))
            await self.update_job_status(job_id, "failed", None, str(e))
    
    async def generate_image(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an image using SDXL."""
        prompt = payload["prompt"]
        negative_prompt = payload.get("negative_prompt", "")
        width = payload.get("width", 1024)
        height = payload.get("height", 1024)
        num_inference_steps = payload.get("num_inference_steps", 20)
        guidance_scale = payload.get("guidance_scale", 7.5)
        seed = payload.get("seed", None)
        
        logger.info("Generating image", prompt=prompt[:50] + "...")
        
        # Load model if not cached
        if "sdxl_pipeline" not in self.models:
            self.models["sdxl_pipeline"] = StableDiffusionXLPipeline.from_pretrained(
                "stabilityai/stable-diffusion-xl-base-1.0",
                torch_dtype=torch.float16,
                use_safetensors=True,
                variant="fp16"
            ).to(self.device)
        
        pipeline = self.models["sdxl_pipeline"]
        
        # Set seed if provided
        if seed is not None:
            torch.manual_seed(seed)
        
        # Generate image
        with torch.autocast(self.device):
            image = pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale
            ).images[0]
        
        # Save image
        output_path = f"/tmp/generated_{int(time.time())}.png"
        image.save(output_path)
        
        # Upload to S3 (implement based on your storage setup)
        s3_url = await self.upload_to_s3(output_path, "outputs/")
        
        # Clean up
        os.remove(output_path)
        
        return {
            "image_url": s3_url,
            "width": width,
            "height": height,
            "seed": seed,
            "prompt": prompt,
            "negative_prompt": negative_prompt
        }
    
    async def generate_video(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a video using AnimateDiff."""
        # TODO: Implement AnimateDiff video generation
        logger.info("Video generation not yet implemented")
        return {"error": "Video generation not yet implemented"}
    
    async def train_lora(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Train a LoRA model."""
        dataset_id = payload["dataset_id"]
        lora_name = payload["lora_name"]
        rank = payload.get("rank", 16)
        steps = payload.get("steps", 1000)
        
        logger.info("Training LoRA", dataset_id=dataset_id, lora_name=lora_name)
        
        # TODO: Implement LoRA training using kohya-ss
        # This would involve:
        # 1. Downloading the dataset from S3
        # 2. Running kohya-ss training script
        # 3. Uploading the trained LoRA to S3
        
        return {
            "lora_name": lora_name,
            "rank": rank,
            "steps": steps,
            "status": "completed"
        }
    
    async def update_job_status(
        self, 
        job_id: int, 
        status: str, 
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ):
        """Update job status in the API."""
        try:
            data = {
                "status": status,
                "result_data": result,
                "error_message": error_message
            }
            
            async with self.session.patch(
                f"{self.api_url}/api/v1/workers/jobs/{job_id}/status",
                headers={"Authorization": f"Bearer {self.worker_token}"},
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    logger.error("Failed to update job status", status=response.status)
                    
        except Exception as e:
            logger.error("Error updating job status", error=str(e))
    
    async def upload_to_s3(self, file_path: str, s3_prefix: str) -> str:
        """Upload file to S3 and return URL."""
        # TODO: Implement S3 upload
        # This would use boto3 to upload to your S3 bucket
        # and return a presigned URL
        
        # For now, return a placeholder
        return f"https://your-bucket.s3.amazonaws.com/{s3_prefix}{os.path.basename(file_path)}"
    
    async def send_heartbeat(self, job_id: int):
        """Send heartbeat for running job."""
        try:
            async with self.session.post(
                f"{self.api_url}/api/v1/workers/jobs/{job_id}/heartbeat",
                headers={"Authorization": f"Bearer {self.worker_token}"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    logger.error("Heartbeat failed", status=response.status)
                    
        except Exception as e:
            logger.error("Error sending heartbeat", error=str(e))


async def main():
    parser = argparse.ArgumentParser(description="AI Generation Platform GPU Worker")
    parser.add_argument("--api-url", required=True, help="API base URL")
    parser.add_argument("--token", required=True, help="Worker authentication token")
    parser.add_argument("--worker-id", help="Worker ID")
    parser.add_argument("--job-type", help="Specific job type to process")
    
    args = parser.parse_args()
    
    worker = GPUWorker(
        api_url=args.api_url,
        worker_token=args.token,
        worker_id=args.worker_id
    )
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error("Worker crashed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


