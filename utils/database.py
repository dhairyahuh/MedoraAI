"""
Shared Database Connection
"""
from sqlalchemy import create_engine, MetaData
import config
import logging

logger = logging.getLogger(__name__)

# Initialize global engine
# SQLAlchemy handles connection pooling automatically
engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)

# Shared metadata for all tables
metadata = MetaData()

def get_engine():
    """Get database engine"""
    return engine

def init_tables():
    """Create all tables defined in metadata"""
    try:
        metadata.create_all(engine)
        logger.info("Database tables verified/created")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
