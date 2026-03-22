"""
JWT Authentication Handler with RS256
Implements secure token generation, validation, and rotation
"""
import jwt
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


class JWTHandler:
    """
    Handles JWT token generation and validation using RS256 (RSA + SHA256)
    
    Why RS256 over HS256:
    - Public key verification (clients can verify without secret)
    - Prevents key confusion attacks
    - Better for distributed systems
    """
    
    def __init__(self, private_key_path: Path, public_key_path: Path):
        """
        Initialize JWT handler with RSA key pair
        
        Args:
            private_key_path: Path to RSA private key (PEM format)
            public_key_path: Path to RSA public key (PEM format)
        """
        self.private_key = self._load_private_key(private_key_path)
        self.public_key = self._load_public_key(public_key_path)
        
        # Token expiration times
        self.ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived
        self.REFRESH_TOKEN_EXPIRE_DAYS = 7     # Longer-lived
        
        # Algorithm
        self.ALGORITHM = "RS256"
        
        logger.info("JWT handler initialized with RS256")
    
    def _load_private_key(self, key_path: Path):
        """Load RSA private key from PEM file"""
        try:
            with open(key_path, 'rb') as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None,  # For production: use encrypted keys
                    backend=default_backend()
                )
            return private_key
        except FileNotFoundError:
            logger.warning(f"Private key not found at {key_path}, generating new key pair...")
            return self._generate_key_pair(key_path)
    
    def _load_public_key(self, key_path: Path):
        """Load RSA public key from PEM file"""
        with open(key_path, 'rb') as key_file:
            public_key = serialization.load_pem_public_key(
                key_file.read(),
                backend=default_backend()
            )
        return public_key
    
    def _generate_key_pair(self, private_key_path: Path):
        """
        Generate new RSA 4096-bit key pair (if keys don't exist)
        
        Security: 4096-bit RSA provides ~152-bit security
        Resistant to quantum attacks (for now)
        """
        logger.info("Generating new RSA 4096-bit key pair...")
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        
        # Save private key
        private_key_path.parent.mkdir(parents=True, exist_ok=True)
        with open(private_key_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Save public key
        public_key_path = private_key_path.parent / "jwt_public.pem"
        public_key = private_key.public_key()
        with open(public_key_path, 'wb') as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
        
        logger.info(f"Key pair generated and saved to {private_key_path.parent}")
        return private_key
    
    def create_access_token(
        self,
        hospital_id: str,
        role: str = "hospital_client",
        permissions: list = None,
        hospital_name: str = "",
        region: str = ""
    ) -> str:
        """
        Create JWT access token
        
        Args:
            hospital_id: Unique hospital identifier
            role: User role (hospital_client, admin, auditor)
            permissions: List of allowed actions
            hospital_name: Human-readable hospital name
            region: Geographic region (for compliance)
        
        Returns:
            Signed JWT token (string)
        """
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        if permissions is None:
            permissions = self._get_default_permissions(role)
        
        payload = {
            # Standard claims (RFC 7519)
            "sub": hospital_id,           # Subject (user ID)
            "iat": now,                    # Issued at
            "exp": expire,                 # Expiration time
            "jti": str(uuid.uuid4()),      # JWT ID (for revocation)
            
            # Custom claims
            "type": "access",
            "role": role,
            "permissions": permissions,
            "hospital_name": hospital_name,
            "region": region
        }
        
        # Sign token with private key
        token = jwt.encode(
            payload,
            self.private_key,
            algorithm=self.ALGORITHM
        )
        
        logger.info(f"Access token created for hospital: {hospital_id}")
        return token
    
    def create_refresh_token(self, hospital_id: str) -> str:
        """
        Create JWT refresh token (longer expiration, fewer claims)
        
        Args:
            hospital_id: Unique hospital identifier
        
        Returns:
            Signed refresh token
        """
        now = datetime.utcnow()
        expire = now + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            "sub": hospital_id,
            "iat": now,
            "exp": expire,
            "jti": str(uuid.uuid4()),
            "type": "refresh"
        }
        
        token = jwt.encode(
            payload,
            self.private_key,
            algorithm=self.ALGORITHM
        )
        
        logger.info(f"Refresh token created for hospital: {hospital_id}")
        return token
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
        
        Returns:
            Decoded token payload
        
        Raises:
            jwt.ExpiredSignatureError: Token has expired
            jwt.InvalidTokenError: Token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.ALGORITHM]
            )
            return payload
        
        except jwt.ExpiredSignatureError:
            logger.warning("Token verification failed: Token expired")
            raise
        
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token verification failed: {e}")
            raise
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Generate new access token from refresh token
        
        Args:
            refresh_token: Valid refresh token
        
        Returns:
            New access token
        
        Raises:
            jwt.InvalidTokenError: Invalid refresh token
        """
        # Verify refresh token
        payload = self.verify_token(refresh_token)
        
        # Ensure it's a refresh token
        if payload.get("type") != "refresh":
            raise jwt.InvalidTokenError("Not a refresh token")
        
        hospital_id = payload.get("sub")
        
        # TODO: Check if token is blacklisted (Redis lookup)
        # TODO: Load hospital role/permissions from database
        
        # Create new access token
        return self.create_access_token(
            hospital_id=hospital_id,
            role="hospital_client",  # TODO: Load from DB
            permissions=["upload_gradients", "download_global_model"]
        )
    
    def _get_default_permissions(self, role: str) -> list:
        """
        Get default permissions for a role
        
        Args:
            role: User role
        
        Returns:
            List of permissions
        """
        role_permissions = {
            "hospital_client": [
                "upload_gradients",
                "download_global_model",
                "view_own_metrics"
            ],
            "admin": [
                "upload_gradients",
                "download_global_model",
                "view_all_metrics",
                "manage_hospitals",
                "configure_fl_params",
                "rollback_model",
                "revoke_access"
            ],
            "auditor": [
                "view_all_metrics",
                "view_audit_logs",
                "generate_reports"
            ]
        }
        
        return role_permissions.get(role, [])
    
    def extract_hospital_id(self, token: str) -> str:
        """
        Extract hospital ID from token without full verification
        (Use only for non-security-critical operations)
        
        Args:
            token: JWT token
        
        Returns:
            Hospital ID (subject claim)
        """
        # Decode without verification (just parse)
        unverified = jwt.decode(token, options={"verify_signature": False})
        return unverified.get("sub")


# Singleton instance
_jwt_handler: Optional[JWTHandler] = None


def get_jwt_handler() -> JWTHandler:
    """Get singleton JWT handler instance"""
    global _jwt_handler
    
    if _jwt_handler is None:
        from pathlib import Path
        keys_dir = Path(__file__).parent / "keys"
        keys_dir.mkdir(exist_ok=True)
        
        _jwt_handler = JWTHandler(
            private_key_path=keys_dir / "jwt_private.pem",
            public_key_path=keys_dir / "jwt_public.pem"
        )
    
    return _jwt_handler


# Example usage
if __name__ == "__main__":
    # Test JWT generation and verification
    handler = get_jwt_handler()
    
    # Create tokens
    access_token = handler.create_access_token(
        hospital_id="hosp_johns_hopkins_001",
        role="hospital_client",
        hospital_name="Johns Hopkins Medical Center",
        region="US-East"
    )
    
    refresh_token = handler.create_refresh_token("hosp_medora_001")
    
    print("Access Token:")
    print(access_token)
    print("\nRefresh Token:")
    print(refresh_token)
    
    # Verify access token
    print("\n--- Verifying Access Token ---")
    try:
        payload = handler.verify_token(access_token)
        print(f"✓ Token valid!")
        print(f"  Hospital: {payload['hospital_name']}")
        print(f"  Role: {payload['role']}")
        print(f"  Permissions: {payload['permissions']}")
        print(f"  Expires: {datetime.fromtimestamp(payload['exp'])}")
    except jwt.InvalidTokenError as e:
        print(f"✗ Token invalid: {e}")
    
    # Test refresh
    print("\n--- Refreshing Access Token ---")
    new_access_token = handler.refresh_access_token(refresh_token)
    print(f"✓ New access token generated")
    print(new_access_token)
