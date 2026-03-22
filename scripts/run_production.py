#!/usr/bin/env python3
"""
Production Server Runner
Use this instead of running main.py directly for production deployments
"""
import sys
import os
import logging
import signal
import uvicorn

# Configure logging before imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/server.log')
    ]
)
logger = logging.getLogger(__name__)

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)


def check_dependencies():
    """Verify all required dependencies are installed"""
    try:
        import torch
        import fastapi
        import prometheus_client
        import psutil
        
        logger.info("✓ All dependencies installed")
        logger.info(f"✓ PyTorch {torch.__version__}")
        logger.info(f"✓ CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            logger.info(f"✓ GPU: {torch.cuda.get_device_name(0)}")
        
        return True
        
    except ImportError as e:
        logger.error(f"✗ Missing dependency: {e}")
        logger.error("Run: pip install -r requirements.txt")
        return False


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Shutdown signal received, stopping server...")
    sys.exit(0)


def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 70)
    logger.info("MEDICAL INFERENCE SERVER - PRODUCTION MODE")
    logger.info("=" * 70)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Load configuration
    import config
    logger.info(f"✓ Device: {config.DEVICE}")
    logger.info(f"✓ Models: {len(config.MODEL_SPECS)} available")
    logger.info(f"✓ Max queue: {config.MAX_QUEUE_SIZE}")
    logger.info(f"✓ Workers: {config.NUM_ASYNC_WORKERS} async, {config.PROCESS_POOL_WORKERS} process")
    
    # Start server
    logger.info("=" * 70)
    logger.info("Starting Uvicorn server...")
    logger.info(f"API: http://{config.HOST}:{config.PORT}")
    logger.info(f"Dashboard: http://{config.HOST}:{config.PORT}/dashboard")
    logger.info(f"Docs: http://{config.HOST}:{config.PORT}/docs")
    logger.info("=" * 70)
    
    try:
        uvicorn.run(
            "main:app",
            host=config.HOST,
            port=config.PORT,
            workers=1,  # Always 1 for GPU inference
            log_level=config.LOG_LEVEL.lower(),
            access_log=True,
            server_header=False,  # Hide server version
            date_header=True,
        )
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
