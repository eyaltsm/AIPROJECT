from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.core.config import settings
import hashlib
import secrets
import uuid
from uuid import uuid4


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(sub: str, role: str, scopes: List[str]) -> str:
    """Create a JWT access token with proper claims."""
    now = datetime.utcnow()
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_TTL_MIN)
    
    claims = {
        "sub": sub,
        "role": role,
        "scopes": scopes,
        "iss": "ai-generation-api",
        "aud": "ai-generation-frontend",
        "jti": uuid4().hex,
        "type": "access",
        "iat": now,
        "exp": expire
    }
    return jwt.encode(claims, settings.ACCESS_TOKEN_SECRET, algorithm="HS256")


def create_refresh_token(sub: str) -> str:
    """Create a JWT refresh token."""
    now = datetime.utcnow()
    expire = now + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS)
    
    claims = {
        "sub": sub,
        "iss": "ai-generation-api",
        "aud": "ai-generation-frontend",
        "jti": uuid4().hex,
        "type": "refresh",
        "iat": now,
        "exp": expire
    }
    return jwt.encode(claims, settings.REFRESH_TOKEN_SECRET, algorithm="HS256")


def create_worker_token(worker_id: str, scopes: List[str]) -> str:
    """Create a worker token for GPU instances."""
    now = datetime.utcnow()
    expire = now + timedelta(hours=24)  # Short-lived for security
    
    claims = {
        "sub": f"worker:{worker_id}",
        "worker_id": worker_id,
        "scopes": scopes,
        "iss": "ai-generation-api",
        "aud": "worker",
        "jti": uuid4().hex,
        "type": "worker",
        "iat": now,
        "exp": expire
    }
    return jwt.encode(claims, settings.WORKER_TOKEN_SECRET, algorithm="HS256")


def verify_access_token(token: str) -> Dict[str, Any]:
    """Verify and decode an access token."""
    try:
        payload = jwt.decode(
            token, 
            settings.ACCESS_TOKEN_SECRET, 
            algorithms=["HS256"],
            audience="ai-generation-frontend",
            issuer="ai-generation-api"
        )
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def verify_refresh_token(token: str) -> Dict[str, Any]:
    """Verify and decode a refresh token."""
    try:
        payload = jwt.decode(
            token, 
            settings.REFRESH_TOKEN_SECRET, 
            algorithms=["HS256"],
            audience="ai-generation-frontend",
            issuer="ai-generation-api"
        )
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def verify_worker_token(token: str) -> Dict[str, Any]:
    """Verify a worker token."""
    try:
        payload = jwt.decode(
            token, 
            settings.WORKER_TOKEN_SECRET, 
            algorithms=["HS256"],
            audience="worker",
            issuer="ai-generation-api"
        )
        if payload.get("type") != "worker":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid worker token"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate worker credentials"
        )


def hash_prompt(prompt: str) -> str:
    """Create a hash of a prompt for audit logging."""
    return hashlib.sha256(prompt.encode()).hexdigest()[:32]


def generate_secure_filename(original_filename: str) -> str:
    """Generate a secure filename with random prefix."""
    ext = original_filename.split('.')[-1] if '.' in original_filename else ''
    random_prefix = secrets.token_urlsafe(16)
    return f"{random_prefix}.{ext}" if ext else random_prefix


def validate_file_type(content_type: str) -> bool:
    """Validate if file type is allowed."""
    return content_type in settings.ALLOWED_IMAGE_TYPES


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    import re
    # Remove any path components and dangerous characters
    filename = re.sub(r'[^\w\-_\.]', '', filename)
    # Ensure it doesn't start with a dot
    filename = filename.lstrip('.')
    return filename[:100]  # Limit length


def is_token_blacklisted(jti: str, redis_client) -> bool:
    """Check if a token is blacklisted."""
    return redis_client.exists(f"blacklist:{jti}") > 0


def blacklist_token(jti: str, redis_client, expire_seconds: int = None):
    """Blacklist a token."""
    if expire_seconds:
        redis_client.setex(f"blacklist:{jti}", expire_seconds, "1")
    else:
        redis_client.set(f"blacklist:{jti}", "1")
