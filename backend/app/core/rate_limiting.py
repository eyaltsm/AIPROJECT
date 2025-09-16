from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from typing import Optional
import redis
from app.core.database import get_redis


def get_user_id_from_token(request: Request) -> Optional[str]:
    """Extract user ID from JWT token for rate limiting."""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        from app.core.security import verify_access_token
        payload = verify_access_token(token)
        return str(payload.get("sub"))
    except Exception:
        return None


def get_rate_limit_key(request: Request) -> str:
    """Generate rate limit key based on user ID or IP address."""
    user_id = get_user_id_from_token(request)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"


# Create rate limiter with custom key function
limiter = Limiter(key_func=get_rate_limit_key)


def get_redis_client() -> redis.Redis:
    """Get Redis client for rate limiting."""
    return get_redis()


