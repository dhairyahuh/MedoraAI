"""
API package initialization
"""
from .routes import router
from .queue_handler import queue_handler
from .auth_routes import router as auth_router
from .federated_routes import router as federated_router
from .schemas import *

__all__ = ['router', 'queue_handler', 'auth_router', 'federated_router']
