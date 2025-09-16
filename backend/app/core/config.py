from pydantic_settings import BaseSettings
from typing import List, Optional
from decimal import Decimal


class Settings(BaseSettings):
    # Environment
    ENV: str = "dev"
    DEBUG: bool = False
    
    # App
    APP_NAME: str = "AI Generation Platform"
    VERSION: str = "1.0.0"
    API_BASE_URL: str = "http://localhost:8000"
    
    # Database
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"
    
    # JWT Secrets (separate for security)
    ACCESS_TOKEN_SECRET: str
    REFRESH_TOKEN_SECRET: str
    WORKER_TOKEN_SECRET: str
    
    # JWT TTL
    ACCESS_TOKEN_TTL_MIN: int = 15
    REFRESH_TOKEN_TTL_DAYS: int = 14
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    # S3 Storage
    S3_ENDPOINT_URL: str
    S3_BUCKET: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_SIGNED_URL_EXPIRE_SECONDS: int = 900  # 15 minutes
    
    # Stripe
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_PUBLISHABLE_KEY: str
    
    # Adult Payment Processors (for NSFW)
    SEGPAY_MERCHANT_ID: Optional[str] = None
    SEGPAY_API_KEY: Optional[str] = None
    
    # GPU Workers
    VAST_AI_API_KEY: str
    RUNPOD_API_KEY: str
    VAST_GPU_FILTER: Optional[str] = "RTX_4090"
    VAST_IMAGE: Optional[str] = None
    GPU_IDLE_TIMEOUT_SEC: int = 180
    STOP_MODE: str = "stop"  # stop | destroy
    
    # Rate Limiting
    RATE_LIMIT_RPM: int = 60
    RATE_LIMIT_BURST: int = 10
    
    # File Upload
    MAX_FILE_SIZE_MB: int = 10
    MAX_IMAGES_PER_DATASET: int = 30
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
    
    # CORS
    FRONTEND_ORIGINS: List[str] = ["http://localhost:3000", "https://yourdomain.com"]
    
    # NSFW Settings
    ENABLE_NSFW: bool = True
    NSFW_CLASSIFIER_THRESHOLD: float = 0.7
    BLOCKLIST_MODE: str = "flag"  # "block" | "flag"
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    
    # Security
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "march-locked-back-pond.trycloudflare.com"]
    
    # LLM Configuration
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    TOGETHER_API_KEY: Optional[str] = None
    
    # LLM Settings
    DEFAULT_LLM_PROVIDER: str = "openai"  # openai, anthropic, groq, together
    LLM_MAX_TOKENS: int = 1000
    LLM_TEMPERATURE: float = 0.7
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
