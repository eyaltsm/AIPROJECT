from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db, get_redis
from app.core.security import verify_access_token, verify_worker_token, is_token_blacklisted
from app.models.user import User, UserRole
import redis


# HTTP Bearer token scheme
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> User:
    """Get current authenticated user."""
    token = credentials.credentials
    
    # Verify token
    payload = verify_access_token(token)
    
    # Check if token is blacklisted
    if is_token_blacklisted(payload.get("jti"), redis_client):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )
    
    # Get user from database
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current user with admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def get_worker_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """Get current worker from token."""
    token = credentials.credentials
    
    # Verify worker token
    payload = verify_worker_token(token)
    
    return {
        "worker_id": payload.get("worker_id"),
        "scopes": payload.get("scopes", []),
        "sub": payload.get("sub")
    }


def require_scopes(required_scopes: list):
    """Dependency factory for requiring specific scopes."""
    def check_scopes(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        redis_client: redis.Redis = Depends(get_redis)
    ):
        token = credentials.credentials
        payload = verify_access_token(token)
        
        # Check if token is blacklisted
        if is_token_blacklisted(payload.get("jti"), redis_client):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        # Check scopes
        user_scopes = payload.get("scopes", [])
        if not all(scope in user_scopes for scope in required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return payload
    
    return check_scopes


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = verify_access_token(token)
        
        # Check if token is blacklisted
        if is_token_blacklisted(payload.get("jti"), redis_client):
            return None
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user or not user.is_active:
            return None
        
        return user
    except HTTPException:
        return None


