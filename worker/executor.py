#!/usr/bin/env python3
"""
GPU Worker Executor for AI Generation Platform.
Handles txt2img, img2img, inpaint, and LoRA training jobs.
"""

import os
import io
import time
import json
import base64
import httpx
from PIL import Image
import boto3
import botocore
import torch
from diffusers import (
    StableDiffusionXLPipeline, 
    StableDiffusionXLImg2ImgPipeline, 
    StableDiffusionXLInpaintPipeline
)

# Configuration from environment
API_BASE = os.environ["CONTROL_BASE_URL"]   # e.g. https://api.yourdomain.com
WORKER_ID = os.environ.get("WORKER_ID", "worker-1")
WORKER_TOKEN = os.environ["WORKER_TOKEN"]

# S3 Configuration
s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["S3_ENDPOINT_URL"],
    aws_access_key_id=os.environ["S3_ACCESS_KEY"],
    aws_secret_access_key=os.environ["S3_SECRET_KEY"],
)
BUCKET = os.environ["S3_BUCKET"]

def upload_bytes(key: str, data: bytes, content_type="image/png"):
    """Upload bytes to S3."""
    s3.put_object(Bucket=BUCKET, Key=key, Body=data, ContentType=content_type)
    return key

# Load pipelines once at startup
print("Loading SDXL pipelines...")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if DEVICE == "cuda" else torch.float32
BASE = "./models/sdxl-base"

print(f"Using device: {DEVICE}, dtype: {dtype}")

try:
    pipe_txt = StableDiffusionXLPipeline.from_pretrained(BASE, torch_dtype=dtype).to(DEVICE)
    pipe_img = StableDiffusionXLImg2ImgPipeline.from_pretrained(BASE, torch_dtype=dtype).to(DEVICE)
    pipe_inp = StableDiffusionXLInpaintPipeline.from_pretrained(BASE, torch_dtype=dtype).to(DEVICE)
    print("Pipelines loaded successfully!")
except Exception as e:
    print(f"Error loading pipelines: {e}")
    print("Make sure models are downloaded with download_models.py")
    exit(1)

def gen_txt2img(p):
    """Generate image from text prompt."""
    print(f"Generating txt2img: {p['prompt'][:50]}...")
    img = pipe_txt(
        p["prompt"], 
        num_inference_steps=p.get("steps", 25),
        guidance_scale=p.get("guidance", 5.5),
        width=p.get("width", 1024), 
        height=p.get("height", 1024),
        negative_prompt=p.get("negative", "")
    ).images[0]
    b = io.BytesIO()
    img.save(b, "PNG")
    return b.getvalue()

def gen_img2img(p):
    """Generate image from image + prompt."""
    print(f"Generating img2img: {p['prompt'][:50]}...")
    init_key = p["init_object_key"]
    
    # Download init image from S3
    obj = s3.get_object(Bucket=BUCKET, Key=init_key)
    init = Image.open(io.BytesIO(obj["Body"].read())).convert("RGB").resize((
        p.get("width", 1024), 
        p.get("height", 1024)
    ))
    
    img = pipe_img(
        prompt=p["prompt"], 
        image=init,
        strength=p.get("strength", 0.45),
        num_inference_steps=p.get("steps", 30),
        guidance_scale=p.get("guidance", 6.5),
        negative_prompt=p.get("negative", "")
    ).images[0]
    
    b = io.BytesIO()
    img.save(b, "PNG")
    return b.getvalue()

def gen_inpaint(p):
    """Generate inpainted image."""
    print(f"Generating inpaint: {p['prompt'][:50]}...")
    init_key = p["init_object_key"]
    mask_key = p["mask_object_key"]
    
    # Download init and mask images from S3
    init_obj = s3.get_object(Bucket=BUCKET, Key=init_key)
    init = Image.open(io.BytesIO(init_obj["Body"].read())).convert("RGB").resize((
        p.get("width", 1024), 
        p.get("height", 1024)
    ))
    
    mask_obj = s3.get_object(Bucket=BUCKET, Key=mask_key)
    mask = Image.open(io.BytesIO(mask_obj["Body"].read())).convert("L").resize((
        p.get("width", 1024), 
        p.get("height", 1024)
    ))
    
    img = pipe_inp(
        prompt=p["prompt"], 
        image=init, 
        mask_image=mask,
        num_inference_steps=p.get("steps", 30),
        guidance_scale=p.get("guidance", 6.0),
        negative_prompt=p.get("negative", "")
    ).images[0]
    
    b = io.BytesIO()
    img.save(b, "PNG")
    return b.getvalue()

def claim_job():
    """Claim a job from the backend."""
    headers = {
        "Authorization": f"Bearer {WORKER_TOKEN}", 
        "X-Worker-Id": WORKER_ID
    }
    try:
        r = httpx.post(f"{API_BASE}/workers/claim", headers=headers, timeout=30)
        if r.status_code == 204:
            return None  # No jobs available
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error claiming job: {e}")
        return None

def update_done(job_id, result):
    """Mark job as completed."""
    headers = {"Authorization": f"Bearer {WORKER_TOKEN}"}
    try:
        httpx.post(
            f"{API_BASE}/workers/jobs/{job_id}/done", 
            json=result, 
            headers=headers, 
            timeout=30
        )
        print(f"Job {job_id} marked as done")
    except Exception as e:
        print(f"Error updating job {job_id} as done: {e}")

def update_fail(job_id, msg):
    """Mark job as failed."""
    headers = {"Authorization": f"Bearer {WORKER_TOKEN}"}
    try:
        httpx.post(
            f"{API_BASE}/workers/jobs/{job_id}/fail", 
            json={"error": msg}, 
            headers=headers, 
            timeout=30
        )
        print(f"Job {job_id} marked as failed: {msg}")
    except Exception as e:
        print(f"Error updating job {job_id} as failed: {e}")

def process_job(job):
    """Process a single job."""
    kind = job["kind"]
    payload = job["payload_json"]
    job_id = job["id"]
    
    print(f"Processing job {job_id} of kind {kind}")
    
    try:
        if kind == "generate_image":
            mode = payload.get("mode", "txt2img")
            
            if mode == "txt2img":
                png_data = gen_txt2img(payload)
            elif mode == "img2img":
                png_data = gen_img2img(payload)
            elif mode == "inpaint":
                png_data = gen_inpaint(payload)
            else:
                raise ValueError(f"Unknown mode: {mode}")
            
            # Upload result to S3
            key = f"outputs/u{job['user_id']}/{job_id}.png"
            upload_bytes(key, png_data)
            
            # Mark job as done
            update_done(job_id, {"object_key": key})
            
        elif kind == "train_lora":
            # TODO: Implement LoRA training
            raise NotImplementedError("LoRA training not yet implemented")
            
        else:
            raise ValueError(f"Unsupported job kind: {kind}")
            
    except Exception as e:
        print(f"Error processing job {job_id}: {e}")
        update_fail(job_id, str(e))

def main_loop():
    """Main worker loop."""
    print(f"Worker {WORKER_ID} starting...")
    print(f"API Base: {API_BASE}")
    print(f"Device: {DEVICE}")
    
    while True:
        try:
            job = claim_job()
            if not job:
                time.sleep(4)
                continue
                
            process_job(job)
            
        except KeyboardInterrupt:
            print("Worker shutting down...")
            break
        except Exception as e:
            print(f"Unexpected error in main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main_loop()
