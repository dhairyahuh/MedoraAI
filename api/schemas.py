"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import Dict, Optional, List
from datetime import datetime
import config


class PredictRequest(BaseModel):
    """Request schema for image prediction"""
    disease_type: str = Field(..., description="Type of disease to detect")
    
    @validator('disease_type')
    def validate_disease_type(cls, v):
        if v not in config.MODEL_ROUTES:
            raise ValueError(f"Invalid disease_type. Must be one of: {list(config.MODEL_ROUTES.keys())}")
        return v


class PredictResponse(BaseModel):
    """Response schema for prediction request"""
    request_id: str
    status: str
    message: Optional[str] = None


class ResultResponse(BaseModel):
    """Response schema for result retrieval"""
    request_id: str
    status: str
    model: Optional[str] = None
    predicted_class: Optional[str] = None
    confidence: Optional[float] = None
    all_probabilities: Optional[Dict[str, float]] = None
    inference_time: Optional[float] = None
    timestamp: Optional[float] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    queue_length: int
    models_loaded: int
    uptime_seconds: float


class MetricsResponse(BaseModel):
    """System metrics response"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_latency: float
    current_queue_length: int
    active_workers: int
    cpu_usage: float
    memory_usage: float


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
