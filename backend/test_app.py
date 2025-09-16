#!/usr/bin/env python3
"""
Simple test app without rate limiting to verify basic functionality.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog
import time
import uuid
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting AI Generation Platform", version=settings.VERSION)
    yield
    # Shutdown
    logger.info("Shutting down AI Generation Platform")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="A secure and scalable AI image/video generation platform.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # Add request ID to request state
    request.state.request_id = request_id

    # Log request details
    logger.info(
        "Request started",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host,
    )

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=f"{process_time:.4f}s",
        client_ip=request.client.host,
    )
    return response

# Health check endpoint
@app.get("/api/health", tags=["Monitoring"])
async def health_check(request: Request):
    return {
        "status": "ok",
        "version": settings.VERSION,
        "request_id": request.state.request_id,
        "timestamp": time.time()
    }

# Test database connection
@app.get("/api/test-db", tags=["Testing"])
async def test_database():
    try:
        # Test database connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1 as test")
            test_value = result.fetchone()[0]
        
        return {
            "status": "ok",
            "database": "connected",
            "test_value": test_value
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "failed",
            "error": str(e)
        }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled exception",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


