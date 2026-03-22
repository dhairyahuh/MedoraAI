"""
Token Bucket Rate Limiter
Implements distributed rate limiting using Redis
"""
import time
import redis
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_minute: int
    burst_size: Optional[int] = None  # Max tokens in bucket (default: capacity)
    
    def __post_init__(self):
        if self.burst_size is None:
            self.burst_size = self.requests_per_minute


class RateLimiter:
    """
    Token Bucket rate limiter with Redis backend
    
    Algorithm:
    - Each user has a "bucket" with tokens
    - Tokens refill at constant rate (requests_per_minute)
    - Each request consumes 1 token
    - If bucket empty → rate limit exceeded
    
    Advantages:
    - Allows bursts (better UX than fixed window)
    - Distributed (works across multiple server instances)
    - Accurate (sliding window, not fixed window)
    """
    
    def __init__(self, redis_client: redis.Redis, prefix: str = "ratelimit"):
        """
        Initialize rate limiter
        
        Args:
            redis_client: Redis connection
            prefix: Key prefix for Redis
        """
        self.redis = redis_client
        self.prefix = prefix
        logger.info("Rate limiter initialized with Redis backend")
    
    def check_limit(
        self,
        identifier: str,
        config: RateLimitConfig
    ) -> Tuple[bool, dict]:
        """
        Check if request is within rate limit
        
        Args:
            identifier: Unique ID (hospital_id, IP address, etc.)
            config: Rate limit configuration
        
        Returns:
            (allowed: bool, metadata: dict)
            metadata contains: remaining, reset_time, retry_after
        """
        key = f"{self.prefix}:{identifier}"
        now = time.time()
        
        # Get current token count and last update time
        pipe = self.redis.pipeline()
        pipe.get(f"{key}:tokens")
        pipe.get(f"{key}:updated")
        results = pipe.execute()
        
        current_tokens = float(results[0]) if results[0] else config.burst_size
        last_updated = float(results[1]) if results[1] else now
        
        # Calculate tokens to add (based on time elapsed)
        time_elapsed = now - last_updated
        refill_rate = config.requests_per_minute / 60.0  # Tokens per second
        tokens_to_add = time_elapsed * refill_rate
        
        # Update token count (capped at burst_size)
        new_tokens = min(config.burst_size, current_tokens + tokens_to_add)
        
        # Check if request allowed
        if new_tokens >= 1.0:
            # Allow request, consume 1 token
            new_tokens -= 1.0
            allowed = True
            
            # Update Redis
            pipe = self.redis.pipeline()
            pipe.setex(f"{key}:tokens", 3600, str(new_tokens))  # 1 hour TTL
            pipe.setex(f"{key}:updated", 3600, str(now))
            pipe.execute()
            
            metadata = {
                "remaining": int(new_tokens),
                "limit": config.requests_per_minute,
                "reset_time": int(now + (config.burst_size - new_tokens) / refill_rate)
            }
        else:
            # Rate limit exceeded
            allowed = False
            
            # Calculate retry_after (seconds until 1 token available)
            retry_after = (1.0 - new_tokens) / refill_rate
            
            metadata = {
                "remaining": 0,
                "limit": config.requests_per_minute,
                "retry_after": int(retry_after) + 1,
                "reset_time": int(now + retry_after)
            }
        
        return allowed, metadata
    
    def reset(self, identifier: str):
        """
        Reset rate limit for identifier
        
        Args:
            identifier: Unique ID to reset
        """
        key = f"{self.prefix}:{identifier}"
        self.redis.delete(f"{key}:tokens", f"{key}:updated")
        logger.info(f"Rate limit reset for {identifier}")
    
    def get_status(self, identifier: str, config: RateLimitConfig) -> dict:
        """
        Get current rate limit status (without consuming tokens)
        
        Args:
            identifier: Unique ID
            config: Rate limit configuration
        
        Returns:
            Status dict with remaining tokens and reset time
        """
        key = f"{self.prefix}:{identifier}"
        now = time.time()
        
        # Get current state
        pipe = self.redis.pipeline()
        pipe.get(f"{key}:tokens")
        pipe.get(f"{key}:updated")
        results = pipe.execute()
        
        current_tokens = float(results[0]) if results[0] else config.burst_size
        last_updated = float(results[1]) if results[1] else now
        
        # Calculate current tokens (with refill)
        time_elapsed = now - last_updated
        refill_rate = config.requests_per_minute / 60.0
        tokens_to_add = time_elapsed * refill_rate
        new_tokens = min(config.burst_size, current_tokens + tokens_to_add)
        
        return {
            "remaining": int(new_tokens),
            "limit": config.requests_per_minute,
            "reset_time": int(now + (config.burst_size - new_tokens) / refill_rate)
        }


class MultiTierRateLimiter:
    """
    Multi-tier rate limiter with different limits for different endpoints
    
    Tiers:
    1. Global (all traffic)
    2. Per-hospital
    3. Per-endpoint
    """
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize multi-tier rate limiter
        
        Args:
            redis_client: Redis connection
        """
        self.global_limiter = RateLimiter(redis_client, prefix="global")
        self.hospital_limiter = RateLimiter(redis_client, prefix="hospital")
        self.endpoint_limiter = RateLimiter(redis_client, prefix="endpoint")
        
        # Default configurations
        self.global_config = RateLimitConfig(requests_per_minute=10000)
        self.hospital_config = RateLimitConfig(requests_per_minute=100)
        
        # Endpoint-specific configs
        self.endpoint_configs = {
            "/api/v1/upload_gradients": RateLimitConfig(requests_per_minute=10),
            "/api/v1/download_model": RateLimitConfig(requests_per_minute=20),
            "/api/v1/metrics": RateLimitConfig(requests_per_minute=100),
            "/api/v1/login": RateLimitConfig(requests_per_minute=5)  # Brute-force protection
        }
        
        logger.info("Multi-tier rate limiter initialized")
    
    def check_all_limits(
        self,
        hospital_id: str,
        endpoint: str
    ) -> Tuple[bool, str, dict]:
        """
        Check all rate limit tiers
        
        Args:
            hospital_id: Hospital identifier
            endpoint: API endpoint path
        
        Returns:
            (allowed: bool, reason: str, metadata: dict)
        """
        # Check global limit
        allowed, metadata = self.global_limiter.check_limit(
            "global",
            self.global_config
        )
        if not allowed:
            return False, "Global rate limit exceeded", metadata
        
        # Check per-hospital limit
        allowed, metadata = self.hospital_limiter.check_limit(
            hospital_id,
            self.hospital_config
        )
        if not allowed:
            return False, "Hospital rate limit exceeded", metadata
        
        # Check endpoint-specific limit (if configured)
        if endpoint in self.endpoint_configs:
            allowed, metadata = self.endpoint_limiter.check_limit(
                f"{hospital_id}:{endpoint}",
                self.endpoint_configs[endpoint]
            )
            if not allowed:
                return False, f"Endpoint rate limit exceeded", metadata
        
        return True, "OK", metadata
    
    def add_endpoint_config(self, endpoint: str, config: RateLimitConfig):
        """
        Add custom rate limit for endpoint
        
        Args:
            endpoint: API endpoint path
            config: Rate limit configuration
        """
        self.endpoint_configs[endpoint] = config
        logger.info(f"Rate limit configured for {endpoint}: {config.requests_per_minute}/min")


# Example usage
if __name__ == "__main__":
    # Connect to Redis
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=False
    )
    
    # Test single-tier rate limiter
    print("--- Testing Token Bucket Rate Limiter ---")
    limiter = RateLimiter(redis_client)
    config = RateLimitConfig(requests_per_minute=60, burst_size=10)  # 1 req/sec, burst of 10
    
    hospital_id = "test_hospital_001"
    
    # Test burst
    print("\nBurst test (should allow 10 requests):")
    for i in range(15):
        allowed, metadata = limiter.check_limit(hospital_id, config)
        status = "✓ ALLOWED" if allowed else "✗ BLOCKED"
        print(f"  Request {i+1}: {status} (remaining: {metadata.get('remaining', 0)})")
    
    # Wait and test refill
    print("\nWaiting 2 seconds for refill...")
    time.sleep(2)
    
    allowed, metadata = limiter.check_limit(hospital_id, config)
    print(f"After refill: {'✓ ALLOWED' if allowed else '✗ BLOCKED'} (remaining: {metadata.get('remaining', 0)})")
    
    # Test multi-tier
    print("\n--- Testing Multi-Tier Rate Limiter ---")
    multi_limiter = MultiTierRateLimiter(redis_client)
    
    # Reset previous tests
    limiter.reset(hospital_id)
    
    # Test endpoint-specific limits
    endpoints = [
        "/api/v1/upload_gradients",
        "/api/v1/download_model",
        "/api/v1/metrics",
        "/api/v1/login"
    ]
    
    for endpoint in endpoints:
        allowed, reason, metadata = multi_limiter.check_all_limits(hospital_id, endpoint)
        print(f"{endpoint}:")
        print(f"  Status: {'✓ ALLOWED' if allowed else '✗ BLOCKED'}")
        print(f"  Remaining: {metadata.get('remaining', 'N/A')}")
    
    # Test login brute-force protection
    print("\n--- Testing Login Brute-Force Protection ---")
    login_endpoint = "/api/v1/login"
    for i in range(10):
        allowed, reason, metadata = multi_limiter.check_all_limits(
            "attacker_hospital",
            login_endpoint
        )
        status = "✓" if allowed else "✗"
        print(f"  Login attempt {i+1}: {status} {reason}")
        if not allowed:
            print(f"    Retry after: {metadata.get('retry_after', 0)} seconds")
    
    print("\n✓ Rate limiter tests complete!")
