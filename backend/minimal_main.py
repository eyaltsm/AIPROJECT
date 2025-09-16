#!/usr/bin/env python3
"""
Minimal FastAPI app to test basic functionality without complex dependencies.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uuid

app = FastAPI(
    title="AI Generation Platform",
    version="1.0.0",
    description="A secure and scalable AI image/video generation platform.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for testing
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # Add request ID to request state
    request.state.request_id = request_id

    response = await call_next(request)

    process_time = time.time() - start_time
    print(f"[{request_id}] {request.method} {request.url} - {response.status_code} ({process_time:.4f}s)")
    
    return response

# Health check endpoint
@app.get("/api/health", tags=["Monitoring"])
async def health_check(request: Request):
    return {
        "status": "ok",
        "version": "1.0.0",
        "request_id": request.state.request_id,
        "timestamp": time.time(),
        "message": "AI Generation Platform is running!"
    }

# Test endpoint
@app.get("/api/test", tags=["Testing"])
async def test_endpoint():
    return {
        "status": "success",
        "message": "Backend is working correctly",
        "features": [
            "FastAPI",
            "CORS",
            "Request logging",
            "Health checks"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
