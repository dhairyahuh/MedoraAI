"""
Rate Limiting Middleware for FastAPI
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
import redis

from security.rate_limiter import MultiTierRateLimiter
from security.jwt_handler import get_jwt_handler

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for multi-tier rate limiting
    
    Applies rate limits automatically to all endpoints
    """
    
    def __init__(self, app, redis_host: str = 'localhost', redis_port: int = 6379):
        super().__init__(app)
        
        # Initialize Redis client
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=0,
                decode_responses=False,
                socket_connect_timeout=2
            )
            self.redis_client.ping()
            self.limiter = MultiTierRateLimiter(self.redis_client)
            self.enabled = True
            logger.info("Rate limiting enabled with Redis backend")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Rate limiting disabled.")
            self.enabled = False
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to requests"""
        
        if not self.enabled:
            return await call_next(request)
        
        # Skip rate limiting for health check and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Extract hospital ID from JWT token
        hospital_id = None
        auth_header = request.headers.get("Authorization", "")
        
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                jwt_handler = get_jwt_handler()
                payload = jwt_handler.verify_token(token)
                hospital_id = payload.get("sub")
            except:
                pass
        
        # Fallback to IP address if no valid token
        if not hospital_id:
            hospital_id = request.client.host if request.client else "unknown"
        
        # Check rate limits
        try:
            allowed, reason, metadata = self.limiter.check_all_limits(
                hospital_id,
                request.url.path
            )
            
            if not allowed:
                return Response(
                    content=f'{{"detail": "{reason}"}}',
                    status_code=429,
                    media_type="application/json",
                    headers={
                        "Retry-After": str(metadata.get("retry_after", 60)),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(metadata.get("reset_time", 0))
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-RateLimit-Remaining"] = str(metadata.get("remaining", 0))
            response.headers["X-RateLimit-Limit"] = str(metadata.get("limit", 100))
            
            return response
        
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Allow request on error (fail open)
            return await call_next(request)
