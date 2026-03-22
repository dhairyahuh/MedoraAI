"""
Authentication Routes for JWT-based access control
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional
import logging
from datetime import datetime

from security.jwt_handler import get_jwt_handler
from security.rate_limiter import RateLimiter, RateLimitConfig
from monitoring.audit_logger import get_audit_logger
import redis

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Security
security = HTTPBearer()

# Redis client for rate limiting (optional)
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False, socket_connect_timeout=1)
    redis_client.ping()
    rate_limiter = RateLimiter(redis_client, prefix="auth")
    logger.info("Redis connected - rate limiting enabled")
except Exception as e:
    logger.warning(f"Redis not available: {e}, rate limiting disabled")
    redis_client = None
    rate_limiter = None


# Request/Response Models
class LoginRequest(BaseModel):
    hospital_id: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes


class RefreshRequest(BaseModel):
    refresh_token: str


# In-memory hospital registry (production: use PostgreSQL)
HOSPITAL_REGISTRY = {
    "hosp_johns_hopkins": {
        "password": "JH_SecurePass_2025!",  # In production: bcrypt hash
        "hospital_name": "Johns Hopkins Medical Center",
        "region": "US-East",
        "role": "hospital_client",
        "active": True
    },
    "hosp_mayo_clinic": {
        "password": "Mayo_SecurePass_2025!",
        "hospital_name": "Mayo Clinic",
        "region": "US-Midwest",
        "role": "hospital_client",
        "active": True
    },
    "admin_user": {
        "password": "Admin_SecurePass_2025!",
        "hospital_name": "System Administrator",
        "region": "Global",
        "role": "admin",
        "active": True
    }
}


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    """
    Authenticate hospital and issue JWT tokens
    
    Returns access token (15 min) and refresh token (7 days)
    """
    try:
        logger.info(f"Login attempt: {credentials.hospital_id}")
        
        # Rate limiting (5 login attempts per minute)
        if rate_limiter:
            config = RateLimitConfig(requests_per_minute=5)
            allowed, metadata = rate_limiter.check_limit(
                credentials.hospital_id,
                config
            )
            if not allowed:
                get_audit_logger().log_authentication(
                    credentials.hospital_id, 
                    False, 
                    "Rate limit exceeded"
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many login attempts. Retry after {metadata.get('retry_after', 60)} seconds"
                )
        
        # 1. Try Database Authentication (New Registrations)
        try:
            from api.user_management import UserManager
            user_manager = UserManager()
            
            # Construct username from hospital_id (e.g. MAYO-01 -> admin_mayo-01)
            # Or assume hospital_id IS the username if they typed "admin_mayo-01"
            # But frontend form asks for "Hospital ID", so we assume admin context.
            
            # Try as constructed admin username
            db_username = f"admin_{credentials.hospital_id.lower()}"
            user = user_manager.authenticate_user(db_username, credentials.password)
            
            # If not found, try as raw username (in case they typed the full username)
            if not user:
                 user = user_manager.authenticate_user(credentials.hospital_id, credentials.password)
                 
            if user:
                logger.info(f"Database login successful: {user.username}")
                
                jwt_handler = get_jwt_handler()
                access_token = jwt_handler.create_access_token(
                    hospital_id=user.hospital_id,
                    role=user.role,
                    hospital_name=user.hospital_name or user.full_name,
                    region=user.region or "Global"
                )
                refresh_token = jwt_handler.create_refresh_token(user.hospital_id)
                
                get_audit_logger().log_authentication(
                    credentials.hospital_id,
                    True,
                    "Login successful (DB)"
                )
                
                return TokenResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=900
                )
                
        except Exception as db_e:
            logger.warning(f"Database auth check failed: {db_e}")
            # Continue to legacy auth...

        # 2. Legacy / Demo Authentication (Fallback)
        hospital = HOSPITAL_REGISTRY.get(credentials.hospital_id)
        
        if not hospital:
            logger.warning(f"Hospital not found: {credentials.hospital_id}")
            get_audit_logger().log_authentication(
                credentials.hospital_id,
                False,
                "Hospital not found"
            )
            # Use same error message to prevent enumeration
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )
        
        if not hospital.get("active"):
            raise HTTPException(status_code=403, detail="Hospital account is inactive")
        
        if credentials.password != hospital["password"]:
            logger.warning(f"Invalid password for: {credentials.hospital_id}")
            get_audit_logger().log_authentication(
                credentials.hospital_id,
                False,
                "Invalid password"
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )
        
        # Generate tokens for legacy user
        jwt_handler = get_jwt_handler()
        access_token = jwt_handler.create_access_token(
            hospital_id=credentials.hospital_id,
            role=hospital["role"],
            hospital_name=hospital["hospital_name"],
            region=hospital["region"]
        )
        refresh_token = jwt_handler.create_refresh_token(credentials.hospital_id)
        
        get_audit_logger().log_authentication(
            credentials.hospital_id,
            True,
            "Login successful (Legacy)"
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=900
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {credentials.hospital_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Authentication service error: {str(e)}"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """
    Refresh access token using refresh token
    """
    jwt_handler = get_jwt_handler()
    
    try:
        # Generate new access token
        new_access_token = jwt_handler.refresh_access_token(request.refresh_token)
        
        # Extract hospital ID for logging
        payload = jwt_handler.verify_token(request.refresh_token)
        hospital_id = payload.get("sub")
        
        logger.info(f"Token refreshed for: {hospital_id}")
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=request.refresh_token,  # Reuse same refresh token
            expires_in=900
        )
    
    except Exception as e:
        logger.warning(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Logout (invalidate tokens)
    
    In production: Add token JTI to Redis blacklist
    """
    token = credentials.credentials
    jwt_handler = get_jwt_handler()
    
    try:
        payload = jwt_handler.verify_token(token)
        hospital_id = payload.get("sub")
        
        # TODO: Blacklist token in Redis
        # token_jti = payload.get("jti")
        # redis_client.setex(f"blacklist:{token_jti}", 900, "1")
        
        get_audit_logger().log_event(
            event_type="authentication",
            actor_hospital_id=hospital_id,
            action="logout",
            resource={"type": "session"},
            result="success"
        )
        
        logger.info(f"Logout: {hospital_id}")
        
        return {"message": "Logged out successfully"}
    
    except Exception as e:
        logger.warning(f"Logout failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


@router.get("/verify")
async def verify_token_endpoint(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify if token is valid (for testing)
    """
    token = credentials.credentials
    jwt_handler = get_jwt_handler()
    
    try:
        payload = jwt_handler.verify_token(token)
        
        return {
            "valid": True,
            "hospital_id": payload.get("sub"),
            "role": payload.get("role"),
            "expires_at": datetime.fromtimestamp(payload.get("exp")).isoformat()
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
