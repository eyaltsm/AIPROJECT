from __future__ import annotations

"""
Lightweight Vast.ai API client and autoscaling helpers.

Env/config (via app.core.config.settings):
  - VAST_API_KEY: API key
  - VAST_GPU_FILTER: Query/filter string for instance type (e.g., 'gpu_name=RTX_4090')
  - VAST_IMAGE: Docker image to run on the instance
  - GPU_IDLE_TIMEOUT_SEC: Idle timeout before shutdown
  - STOP_MODE: 'stop' | 'destroy'

We persist the active instance id in Redis under key 'vast:active_instance_id'.
"""

import os
import time
from typing import Optional, Dict, Any
import httpx
import structlog

from app.core.config import settings
from app.core.database import redis_client


logger = structlog.get_logger()

API_BASE = "https://api.vast.ai"  # Public Vast.ai API base


def _headers() -> Dict[str, str]:
    api_key = settings.VAST_AI_API_KEY
    if not api_key:
        raise RuntimeError("VAST_API_KEY is not set")
    return {"Authorization": f"Bearer {api_key}"}


def get_active_instance_id() -> Optional[str]:
    return redis_client.get("vast:active_instance_id")


def set_active_instance_id(instance_id: Optional[str]) -> None:
    key = "vast:active_instance_id"
    if instance_id:
        redis_client.set(key, instance_id)
    else:
        redis_client.delete(key)


def _is_instance_running(instance_id: str) -> bool:
    try:
        with httpx.Client(timeout=20) as client:
            r = client.get(f"{API_BASE}/v0/instances/{instance_id}", headers=_headers())
            if r.status_code != 200:
                return False
            data = r.json()
            # Heuristic: Vast returns 'state' or 'status' fields; treat 'running' as ready
            state = str(data.get("state") or data.get("status") or "").lower()
            return "run" in state
    except Exception as e:
        logger.warn("vast_is_running_check_failed", error=str(e))
        return False


def ensure_gpu_instance() -> Optional[str]:
    """Start a Vast.ai instance if none is running. Returns instance id (str) or None."""
    try:
        existing = get_active_instance_id()
        if existing and _is_instance_running(existing):
            logger.info("vast_instance_already_running", instance_id=existing)
            return existing

        # Create/start instance
        payload = {
            # These fields are representative; adjust to your Vast templates
            "image": settings.VAST_IMAGE,
            "gpu": settings.VAST_GPU_FILTER or "RTX_4090",
            "onstart": "bash -lc 'cd ~/Aiproject/worker && ./onstart.sh'",
        }
        with httpx.Client(timeout=60) as client:
            r = client.post(f"{API_BASE}/v0/instances", headers=_headers(), json=payload)
            r.raise_for_status()
            data = r.json()
            instance_id = str(data.get("id") or data.get("instance_id"))
            if not instance_id:
                logger.error("vast_create_no_id", response=data)
                return None
            set_active_instance_id(instance_id)
            logger.info("vast_instance_started", instance_id=instance_id)
            return instance_id
    except Exception as e:
        logger.error("vast_ensure_failed", error=str(e))
        return None


def stop_instance(instance_id: str) -> bool:
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(f"{API_BASE}/v0/instances/{instance_id}/stop", headers=_headers())
            if r.status_code in (200, 202, 204):
                logger.info("vast_instance_stopped", instance_id=instance_id)
                set_active_instance_id(None)
                return True
            logger.error("vast_stop_failed", status=r.status_code, body=r.text)
            return False
    except Exception as e:
        logger.error("vast_stop_exception", error=str(e))
        return False


def destroy_instance(instance_id: str) -> bool:
    try:
        with httpx.Client(timeout=30) as client:
            r = client.delete(f"{API_BASE}/v0/instances/{instance_id}", headers=_headers())
            if r.status_code in (200, 202, 204):
                logger.info("vast_instance_destroyed", instance_id=instance_id)
                set_active_instance_id(None)
                return True
            logger.error("vast_destroy_failed", status=r.status_code, body=r.text)
            return False
    except Exception as e:
        logger.error("vast_destroy_exception", error=str(e))
        return False


def maybe_shutdown_gpu(idle_seconds: int) -> None:
    instance_id = get_active_instance_id()
    if not instance_id:
        return
    if idle_seconds < (settings.GPU_IDLE_TIMEOUT_SEC or 180):
        return
    if (settings.STOP_MODE or "stop").lower() == "destroy":
        destroy_instance(instance_id)
    else:
        stop_instance(instance_id)


