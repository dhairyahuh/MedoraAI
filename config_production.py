"""
Production Configuration
Environment-specific settings for deployment
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models" / "weights"
STATIC_DIR = BASE_DIR / "static"
LOGS_DIR = BASE_DIR / "logs"
CERTS_DIR = BASE_DIR / "certs"

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8443))  # HTTPS port
WORKERS = int(os.getenv("WORKERS", 4))  # More workers for production
RELOAD = False  # Never reload in production

# TLS/SSL Configuration
ENABLE_TLS = os.getenv("ENABLE_TLS", "true").lower() == "true"
CERT_FILE = CERTS_DIR / "server.crt"
KEY_FILE = CERTS_DIR / "server.key"

# Redis Configuration (for rate limiting and caching)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Database Configuration (PostgreSQL)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fedmed_user:secure_password@localhost:5432/fedmed_db"
)

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_THIS_IN_PRODUCTION_USE_LONG_RANDOM_STRING")
JWT_ALGORITHM = "RS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

# Encryption Configuration
ENCRYPTION_MASTER_KEY = os.getenv("ENCRYPTION_MASTER_KEY", None)  # Load from KMS in production

# Differential Privacy Configuration
DP_EPSILON = float(os.getenv("DP_EPSILON", "1.0"))
DP_DELTA = float(os.getenv("DP_DELTA", "1e-5"))
DP_CLIPPING_NORM = float(os.getenv("DP_CLIPPING_NORM", "1.0"))

# Federated Learning Configuration
MIN_HOSPITALS_PER_ROUND = int(os.getenv("MIN_HOSPITALS_PER_ROUND", "3"))
MAX_ROUNDS = int(os.getenv("MAX_ROUNDS", "1000"))

# Rate Limiting Configuration
RATE_LIMIT_GLOBAL = int(os.getenv("RATE_LIMIT_GLOBAL", "10000"))  # requests/minute
RATE_LIMIT_PER_HOSPITAL = int(os.getenv("RATE_LIMIT_PER_HOSPITAL", "100"))
RATE_LIMIT_LOGIN = int(os.getenv("RATE_LIMIT_LOGIN", "5"))
RATE_LIMIT_UPLOAD_GRADIENTS = int(os.getenv("RATE_LIMIT_UPLOAD_GRADIENTS", "10"))

# Monitoring Configuration
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))
ENABLE_METRICS = True
ENABLE_AUDIT_LOGS = True

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "production.log"
AUDIT_LOG_DIR = LOGS_DIR / "audit"

# CORS Configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Security Headers
HSTS_MAX_AGE = 31536000  # 1 year
HSTS_INCLUDE_SUBDOMAINS = True

# Model Configuration
DEVICE = os.getenv("DEVICE", "cuda" if __import__("torch").cuda.is_available() else "cpu")
MODEL_BATCH_SIZE = int(os.getenv("MODEL_BATCH_SIZE", "8"))
MODEL_TIMEOUT = int(os.getenv("MODEL_TIMEOUT", "30"))

# Image Processing
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".dcm"}
IMAGE_SIZE = (224, 224)

# Queue Configuration
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "10000"))
NUM_ASYNC_WORKERS = int(os.getenv("NUM_ASYNC_WORKERS", "8"))
PROCESS_POOL_WORKERS = int(os.getenv("PROCESS_POOL_WORKERS", "16"))

# Performance Thresholds
MAX_RESPONSE_TIME = float(os.getenv("MAX_RESPONSE_TIME", "2.0"))
MAX_QUEUE_WAIT_TIME = float(os.getenv("MAX_QUEUE_WAIT_TIME", "5.0"))
MIN_SUCCESS_RATE = float(os.getenv("MIN_SUCCESS_RATE", "0.999"))

# Health Check Configuration
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))  # seconds

print(f"""
╔══════════════════════════════════════════════════════════╗
║  Production Configuration Loaded                         ║
╠══════════════════════════════════════════════════════════╣
║  TLS: {ENABLE_TLS}                                        ║
║  Port: {PORT}                                               ║
║  Workers: {WORKERS}                                           ║
║  Device: {DEVICE}                                          ║
║  Redis: {REDIS_HOST}:{REDIS_PORT}                            ║
║  DP Privacy: ε={DP_EPSILON}, δ={DP_DELTA}                    ║
║  Rate Limit: {RATE_LIMIT_PER_HOSPITAL}/min per hospital            ║
╚══════════════════════════════════════════════════════════╝
""")
