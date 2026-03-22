"""
Federated Learning Routes for secure gradient aggregation
"""
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import logging
import io
import asyncio
from collections import defaultdict

from security.jwt_handler import get_jwt_handler
from security.crypto_handler import get_crypto_handler
from federated.fedavg import FederatedAveraging, ByzantineRobustAggregation
from federated.differential_privacy import DifferentialPrivacy
from federated.model_manager import get_federated_manager
from monitoring.audit_logger import get_audit_logger
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/api/v1/federated", tags=["Federated Learning"])

# Security
security = HTTPBearer()

# Federated learning state
class FederatedState:
    def __init__(self):
        # Create simple model for demonstration (production: use CheXNet)
        self.global_model = nn.Sequential(
            nn.Linear(224*224*3, 128),
            nn.ReLU(),
            nn.Linear(128, 14)  # 14 diseases (ChestX-ray14)
        )
        self.fedavg = FederatedAveraging(self.global_model, learning_rate=1.0)
        self.dp_handler = DifferentialPrivacy(epsilon=1.0, delta=1e-5, clipping_norm=1.0)
        self.gradient_buffer = defaultdict(dict)
        self.current_round = 0
        self.min_hospitals_per_round = 3
        self.aggregation_lock = asyncio.Lock()

federated_state = FederatedState()


# Request/Response Models
class GradientUploadResponse(BaseModel):
    status: str
    hospital_id: str
    round: int
    hospitals_waiting: int
    privacy_budget_remaining: float


class ModelDownloadResponse(BaseModel):
    round: int
    model_version: str
    file_size_bytes: int


async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and extract payload"""
    token = credentials.credentials
    jwt_handler = get_jwt_handler()
    
    try:
        payload = jwt_handler.verify_token(token)
        
        # Check permissions
        permissions = payload.get("permissions", [])
        if "upload_gradients" not in permissions and payload.get("role") != "admin":
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions for federated learning"
            )
        
        return payload
    
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )


@router.post("/upload_gradients", response_model=GradientUploadResponse)
async def upload_gradients(
    encrypted_file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    token_payload: dict = Depends(verify_jwt_token)
):
    """
    Hospital uploads encrypted local gradients
    
    Steps:
    1. Verify JWT token
    2. Decrypt gradient file
    3. Apply differential privacy
    4. Store in aggregation buffer
    5. Trigger aggregation if enough gradients
    """
    hospital_id = token_payload.get("sub")
    if not hospital_id:
        raise HTTPException(status_code=400, detail="Invalid token: missing hospital_id")
    
    logger.info(f"Receiving gradients from {hospital_id}")
    
    # Read encrypted file
    encrypted_bytes = await encrypted_file.read()
    
    # Decrypt gradients
    crypto = get_crypto_handler()
    try:
        gradients = crypto.decrypt_gradients(encrypted_bytes, hospital_id)
    except Exception as e:
        logger.error(f"Gradient decryption failed for {hospital_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail="Failed to decrypt gradients. Check encryption key."
        )
    
    # Validate gradient shapes
    expected_params = list(federated_state.global_model.state_dict().keys())
    if set(gradients.keys()) != set(expected_params):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid gradient structure. Expected {len(expected_params)} parameters."
        )
    
    # Apply differential privacy
    if not federated_state.dp_handler.has_privacy_budget():
        raise HTTPException(
            status_code=403,
            detail="Privacy budget exhausted. Training complete."
        )
    
    private_gradients = federated_state.dp_handler.privatize_gradients(
        gradients,
        device='cpu'
    )
    
    # Store in buffer
    async with federated_state.aggregation_lock:
        federated_state.gradient_buffer[federated_state.current_round][hospital_id] = private_gradients
        
        hospitals_waiting = len(federated_state.gradient_buffer[federated_state.current_round])
        
        # Record in federated manager
        manager = get_federated_manager()
        await manager.record_gradient_upload(hospital_id, private_gradients)
        
        # Log upload
        get_audit_logger().log_gradient_upload(
            hospital_id,
            federated_state.current_round,
            len(encrypted_bytes)
        )
        
        # Trigger aggregation if enough hospitals
        if hospitals_waiting >= federated_state.min_hospitals_per_round:
            background_tasks.add_task(aggregate_and_update_model)
    
    eps_spent, eps_remaining = federated_state.dp_handler.get_privacy_spent()
    
    return GradientUploadResponse(
        status="accepted",
        hospital_id=hospital_id,
        round=federated_state.current_round,
        hospitals_waiting=hospitals_waiting,
        privacy_budget_remaining=eps_remaining
    )


@router.get("/download_model")
async def download_model(
    token_payload: dict = Depends(verify_jwt_token)
):
    """
    Hospital downloads encrypted global model
    """
    hospital_id = token_payload.get("sub")
    if not hospital_id:
        raise HTTPException(status_code=400, detail="Invalid token: missing hospital_id")
    
    # Check permissions
    permissions = token_payload.get("permissions", [])
    if "download_global_model" not in permissions and token_payload.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to download model"
        )
    
    logger.info(f"Hospital {hospital_id} downloading model (round {federated_state.current_round})")
    
    # Get global model state
    global_state = federated_state.fedavg.get_global_model_state()
    
    # Encrypt for hospital
    crypto = get_crypto_handler()
    encrypted_bytes = crypto.encrypt_model(global_state, hospital_id)
    
    # Record in federated manager
    manager = get_federated_manager()
    await manager.record_model_download(hospital_id)
    
    # Log download
    get_audit_logger().log_model_download(
        hospital_id,
        f"round_{federated_state.current_round}"
    )
    
    # Return as streaming response
    return StreamingResponse(
        io.BytesIO(encrypted_bytes),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename=global_model_r{federated_state.current_round}.enc",
            "X-Model-Round": str(federated_state.current_round),
            "X-Model-Size": str(len(encrypted_bytes))
        }
    )


@router.get("/status")
async def get_federated_status(token_payload: dict = Depends(verify_jwt_token)):
    """
    Get current federated learning status
    """
    eps_spent, eps_remaining = federated_state.dp_handler.get_privacy_spent()
    
    # Get manager statistics
    manager = get_federated_manager()
    stats = manager.get_statistics()
    
    return {
        "current_round": federated_state.current_round,
        "hospitals_in_current_round": len(federated_state.gradient_buffer.get(federated_state.current_round, {})),
        "min_hospitals_required": federated_state.min_hospitals_per_round,
        "privacy_budget": {
            "epsilon_spent": eps_spent,
            "epsilon_remaining": eps_remaining,
            "epsilon_total": federated_state.dp_handler.epsilon
        },
        "total_training_steps": federated_state.dp_handler.steps,
        "federated_stats": stats
    }


@router.post("/report_metrics")
async def report_metrics(
    metrics: dict,
    token_payload: dict = Depends(verify_jwt_token)
):
    """
    Hospital reports local vs global accuracy metrics
    """
    hospital_id = token_payload.get("sub")
    if not hospital_id:
        raise HTTPException(status_code=400, detail="Invalid token: missing hospital_id")
    
    local_accuracy = metrics.get("local_accuracy")
    global_accuracy = metrics.get("global_accuracy")
    
    # Update manager
    manager = get_federated_manager()
    manager.update_hospital_metrics(
        hospital_id=hospital_id,
        local_accuracy=local_accuracy,
        global_accuracy=global_accuracy
    )
    
    return {"status": "success", "hospital_id": hospital_id}


async def aggregate_and_update_model():
    """
    Background task: Aggregate gradients with Byzantine defense and update global model
    """
    async with federated_state.aggregation_lock:
        round_num = federated_state.current_round
        gradients_dict = federated_state.gradient_buffer.get(round_num, {})
        
        if len(gradients_dict) < federated_state.min_hospitals_per_round:
            logger.warning(f"Not enough gradients for round {round_num}")
            return
        
        logger.info(f"Aggregating gradients from {len(gradients_dict)} hospitals (round {round_num})")
        
        # Convert to list
        hospital_ids = list(gradients_dict.keys())
        gradients_list = list(gradients_dict.values())
        
        # Byzantine-robust aggregation (Krum)
        selected_indices = ByzantineRobustAggregation.krum(
            gradients_list,
            num_byzantine=1,
            multi_krum=True  # Select multiple gradients
        )
        
        # Filter to selected gradients
        selected_gradients = [gradients_list[i] for i in selected_indices]
        
        logger.info(f"Krum selected {len(selected_gradients)}/{len(gradients_list)} gradients")
        
        # FedAvg aggregation
        aggregated = federated_state.fedavg.aggregate_gradients(selected_gradients)
        
        # Update global model
        federated_state.fedavg.apply_aggregated_gradient(aggregated)
        
        # Get updated global model state
        global_state = federated_state.fedavg.get_global_model_state()
        
        # Notify federated manager (triggers distribution to hospitals)
        manager = get_federated_manager()
        await manager.aggregate_and_distribute(global_state)
        
        # Clear buffer and increment round
        del federated_state.gradient_buffer[round_num]
        federated_state.current_round += 1
        
        logger.info(f"✓ Federated learning round {round_num} complete. Now on round {federated_state.current_round}")
