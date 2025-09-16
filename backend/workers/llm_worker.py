#!/usr/bin/env python3
"""
LLM Worker for AI Generation Platform
Handles local LLM inference for prompt generation and chat
"""

import asyncio
import argparse
import json
import time
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import aiohttp
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
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


class LLMWorker:
    """LLM worker for processing text generation jobs."""
    
    def __init__(self, api_url: str, worker_token: str, worker_id: str = None):
        self.api_url = api_url
        self.worker_token = worker_token
        self.worker_id = worker_id or f"llm-worker-{os.getpid()}"
        self.session = None
        
        # Model cache
        self.models = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info("LLM Worker initialized", worker_id=self.worker_id, device=self.device)
    
    async def start(self):
        """Start the worker main loop."""
        logger.info("Starting LLM worker", worker_id=self.worker_id)
        
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
                json={"job_kinds": ["generate_prompt", "chat_completion", "analyze_image"]},
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
        
        logger.info("Processing LLM job", job_id=job_id, kind=job_kind)
        
        try:
            if job_kind == "generate_prompt":
                result = await self.generate_prompt(payload)
            elif job_kind == "chat_completion":
                result = await self.chat_completion(payload)
            elif job_kind == "analyze_image":
                result = await self.analyze_image(payload)
            else:
                raise ValueError(f"Unknown job kind: {job_kind}")
            
            # Update job as completed
            await self.update_job_status(job_id, "completed", result)
            logger.info("Job completed successfully", job_id=job_id)
            
        except Exception as e:
            logger.error("Job failed", job_id=job_id, error=str(e))
            await self.update_job_status(job_id, "failed", None, str(e))
    
    async def generate_prompt(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a detailed prompt for image generation."""
        user_input = payload["user_input"]
        style = payload.get("style", "photorealistic")
        model_name = payload.get("model", "llama-3.1-8b")
        
        logger.info("Generating prompt", user_input=user_input[:50] + "...")
        
        # Load model if not cached
        if model_name not in self.models:
            await self.load_llm_model(model_name)
        
        model, tokenizer = self.models[model_name]
        
        # Create prompt
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
        
        # Generate response
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create a detailed prompt for: {user_input}"}
        ]
        
        response = await self.generate_response(messages, model, tokenizer)
        
        return {
            "prompt": response,
            "model": model_name,
            "style": style,
            "user_input": user_input
        }
    
    async def chat_completion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat completion requests."""
        messages = payload["messages"]
        model_name = payload.get("model", "llama-3.1-8b")
        
        logger.info("Processing chat completion", model=model_name)
        
        # Load model if not cached
        if model_name not in self.models:
            await self.load_llm_model(model_name)
        
        model, tokenizer = self.models[model_name]
        
        # Generate response
        response = await self.generate_response(messages, model, tokenizer)
        
        return {
            "message": response,
            "model": model_name,
            "messages": messages
        }
    
    async def analyze_image(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze an image using vision models."""
        image_url = payload["image_url"]
        analysis_type = payload.get("analysis_type", "describe")
        model_name = payload.get("model", "llama-3.1-8b")
        
        logger.info("Analyzing image", analysis_type=analysis_type, model=model_name)
        
        # For now, return a placeholder since vision models require special setup
        # In production, you'd use a vision-language model like LLaVA or GPT-4V
        
        return {
            "analysis": f"Image analysis using {model_name} - {analysis_type}",
            "analysis_type": analysis_type,
            "model": model_name,
            "image_url": image_url
        }
    
    async def load_llm_model(self, model_name: str):
        """Load an LLM model."""
        logger.info("Loading LLM model", model=model_name)
        
        model_paths = {
            "llama-3.1-8b": "/opt/ai-worker/models/llm/llama-3.1-8b",
            "llama-3.1-70b": "/opt/ai-worker/models/llm/llama-3.1-70b",
            "mistral-7b": "/opt/ai-worker/models/llm/mistral-7b",
            "qwen-2.5-72b": "/opt/ai-worker/models/llm/qwen-2.5-72b"
        }
        
        model_path = model_paths.get(model_name)
        if not model_path or not os.path.exists(model_path):
            # Fallback to Hugging Face Hub
            model_path = f"meta-llama/Llama-3.1-8B-Instruct"  # Default fallback
        
        try:
            # Load tokenizer and model
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.float16,
                device_map="auto" if torch.cuda.is_available() else None
            )
            
            self.models[model_name] = (model, tokenizer)
            logger.info("Model loaded successfully", model=model_name)
            
        except Exception as e:
            logger.error("Failed to load model", model=model_name, error=str(e))
            raise
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        model, 
        tokenizer
    ) -> str:
        """Generate a response using the model."""
        # Convert messages to prompt format
        prompt = self.format_messages(messages)
        
        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Generate response
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Decode response
        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        
        return response.strip()
    
    def format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for the model."""
        prompt = ""
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                prompt += f"System: {content}\n\n"
            elif role == "user":
                prompt += f"Human: {content}\n\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n\n"
        
        prompt += "Assistant:"
        return prompt
    
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


async def main():
    parser = argparse.ArgumentParser(description="AI Generation Platform LLM Worker")
    parser.add_argument("--api-url", required=True, help="API base URL")
    parser.add_argument("--token", required=True, help="Worker authentication token")
    parser.add_argument("--worker-id", help="Worker ID")
    
    args = parser.parse_args()
    
    worker = LLMWorker(
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


