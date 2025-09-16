from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings
import redis

# Database engine with proper configuration
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_pre_ping=True,
    pool_recycle=300,
    future=True,
    echo=settings.DEBUG,
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine, 
    autoflush=False, 
    autocommit=False, 
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()

# Redis for caching and rate limiting
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Dependency to get Redis client
def get_redis():
    return redis_client
