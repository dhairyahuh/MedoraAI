"""
Federated Learning Model Manager
Coordinates global model lifecycle and hospital synchronization
"""
import logging
import asyncio
import torch
import torch.nn as nn
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class HospitalParticipant:
    """Hospital participating in federated learning"""
    hospital_id: str
    last_gradient_upload: Optional[datetime] = None
    last_model_download: Optional[datetime] = None
    total_gradients_uploaded: int = 0
    total_models_downloaded: int = 0
    local_accuracy: float = 0.0
    global_accuracy: float = 0.0
    is_active: bool = True
    

@dataclass
class FederatedRound:
    """Single federated learning round"""
    round_number: int
    start_time: datetime
    end_time: Optional[datetime] = None
    participating_hospitals: Set[str] = field(default_factory=set)
    gradients_received: int = 0
    global_model_accuracy: float = 0.0
    status: str = "in_progress"  # in_progress, completed, failed


class FederatedModelManager:
    """
    Manages federated learning lifecycle:
    - Coordinates training rounds
    - Distributes global model to hospitals
    - Tracks performance metrics
    - Schedules automatic training
    """
    
    def __init__(
        self,
        model_dir: Path = Path("models/federated"),
        min_hospitals: int = 3,
        round_duration_hours: int = 24
    ):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.min_hospitals = min_hospitals
        self.round_duration = timedelta(hours=round_duration_hours)
        
        # State
        self.hospitals: Dict[str, HospitalParticipant] = {}
        self.rounds: List[FederatedRound] = []
        self.current_round: Optional[FederatedRound] = None
        
        # Global model (simple demo - replace with actual CheXNet in production)
        self.global_model = nn.Sequential(
            nn.Linear(224*224*3, 128),
            nn.ReLU(),
            nn.Linear(128, 14)  # 14 diseases
        )
        
        # Notification callbacks
        self.model_ready_callbacks: List[callable] = []
        
        logger.info(f"FederatedModelManager initialized (min {min_hospitals} hospitals, {round_duration_hours}h rounds)")
    
    
    def register_hospital(self, hospital_id: str):
        """Register a new hospital participant"""
        if hospital_id not in self.hospitals:
            self.hospitals[hospital_id] = HospitalParticipant(hospital_id=hospital_id)
            logger.info(f"Registered hospital: {hospital_id}")
        return self.hospitals[hospital_id]
        
    def sync_with_db(self):
        """Sync in-memory hospital list with database"""
        try:
            from api.user_management import users_table, engine
            from sqlalchemy import select
            
            with engine.connect() as conn:
                # Find all hospital admins
                stmt = select(users_table).where(users_table.c.role.in_(['hospital_admin', 'hospital_client']))
                rows = conn.execute(stmt).all()
                
                for row in rows:
                    if row.hospital_id and row.hospital_id not in self.hospitals:
                        self.register_hospital(row.hospital_id)
                        # Initialize metadata if available
                        if hasattr(row, 'local_accuracy') and row.local_accuracy:
                            self.hospitals[row.hospital_id].local_accuracy = row.local_accuracy
                        if hasattr(row, 'global_accuracy') and row.global_accuracy:
                             self.hospitals[row.hospital_id].global_accuracy = row.global_accuracy
                             
        except Exception as e:
            logger.warning(f"Failed to sync hospitals from DB: {e}")
    
    
    def start_new_round(self) -> FederatedRound:
        """Start a new federated learning round"""
        round_number = len(self.rounds) + 1
        
        self.current_round = FederatedRound(
            round_number=round_number,
            start_time=datetime.now()
        )
        self.rounds.append(self.current_round)
        
        logger.info(f"Started federated learning round {round_number}")
        return self.current_round
    
    
    async def record_gradient_upload(self, hospital_id: str, gradients: Dict[str, torch.Tensor]):
        """Record when a hospital uploads gradients"""
        hospital = self.hospitals.get(hospital_id)
        if not hospital:
            hospital = self.register_hospital(hospital_id)
        
        hospital.last_gradient_upload = datetime.now()
        hospital.total_gradients_uploaded += 1
        
        if self.current_round:
            self.current_round.participating_hospitals.add(hospital_id)
            self.current_round.gradients_received += 1
            
            logger.info(
                f"Hospital {hospital_id} uploaded gradients for round {self.current_round.round_number} "
                f"({self.current_round.gradients_received}/{self.min_hospitals} received)"
            )
    
    
    async def aggregate_and_distribute(self, aggregated_state: Dict[str, torch.Tensor]):
        """
        After aggregation, update global model and notify hospitals
        
        Args:
            aggregated_state: Aggregated model state dict
        """
        if not self.current_round:
            logger.warning("No active round to complete")
            return
        
        # Update global model
        self.global_model.load_state_dict(aggregated_state)
        
        # Save global model
        model_path = self.model_dir / f"global_model_round_{self.current_round.round_number}.pth"
        torch.save(aggregated_state, model_path)
        
        # Mark round complete
        self.current_round.end_time = datetime.now()
        self.current_round.status = "completed"
        
        logger.info(
            f"Round {self.current_round.round_number} completed with "
            f"{len(self.current_round.participating_hospitals)} hospitals"
        )
        
        # Notify all hospitals that new model is ready
        await self._notify_hospitals_model_ready()
        
        # Start next round automatically
        self.start_new_round()
    
    
    async def _notify_hospitals_model_ready(self):
        """Notify all registered hospitals that global model is ready for download"""
        logger.info(f"Notifying {len(self.hospitals)} hospitals: global model ready")
        
        # Call registered callbacks
        for callback in self.model_ready_callbacks:
            try:
                await callback(self.current_round)
            except Exception as e:
                logger.error(f"Model ready callback failed: {e}")
        
        # In production, this would:
        # - Send push notifications to hospitals
        # - Email admins
        # - Update hospital dashboards
        # - Auto-trigger download for configured hospitals
    
    
    def on_model_ready(self, callback: callable):
        """Register callback for when global model is ready"""
        self.model_ready_callbacks.append(callback)
    
    
    async def record_model_download(self, hospital_id: str):
        """Record when a hospital downloads the global model"""
        hospital = self.hospitals.get(hospital_id)
        if not hospital:
            hospital = self.register_hospital(hospital_id)
        
        hospital.last_model_download = datetime.now()
        hospital.total_models_downloaded += 1
        
        logger.info(f"Hospital {hospital_id} downloaded global model (round {self.current_round.round_number if self.current_round else 'N/A'})")
    
    
    def update_hospital_metrics(
        self,
        hospital_id: str,
        local_accuracy: Optional[float] = None,
        global_accuracy: Optional[float] = None
    ):
        """Update performance metrics for a hospital"""
        hospital = self.hospitals.get(hospital_id)
        if not hospital:
            hospital = self.register_hospital(hospital_id)
        
        if local_accuracy is not None:
            hospital.local_accuracy = local_accuracy
        if global_accuracy is not None:
            hospital.global_accuracy = global_accuracy
        
        # Log improvement
        if hospital.local_accuracy > 0 and hospital.global_accuracy > 0:
            improvement = hospital.global_accuracy - hospital.local_accuracy
            improvement_pct = (improvement / hospital.local_accuracy) * 100
            
            logger.info(
                f"Hospital {hospital_id}: Local={hospital.local_accuracy:.2%}, "
                f"Global={hospital.global_accuracy:.2%} "
                f"({'↑' if improvement > 0 else '↓'} {abs(improvement_pct):.1f}%)"
            )
    
    
    def get_current_global_model_path(self) -> Optional[Path]:
        """Get path to current global model"""
        if not self.current_round or self.current_round.round_number == 1:
            return None
        
        # Return previous round's model (current round is in progress)
        round_num = self.current_round.round_number - 1
        model_path = self.model_dir / f"global_model_round_{round_num}.pth"
        
        if model_path.exists():
            return model_path
        return None
    
    
    def get_statistics(self) -> Dict:
        """Get federated learning statistics"""
        # Sync with database to get newly registered hospitals
        self.sync_with_db()
        
        total_hospitals = len(self.hospitals)
        active_hospitals = sum(1 for h in self.hospitals.values() if h.is_active)
        
        # Average improvements
        improvements = []
        for hospital in self.hospitals.values():
            if hospital.local_accuracy > 0 and hospital.global_accuracy > 0:
                improvement = hospital.global_accuracy - hospital.local_accuracy
                improvements.append(improvement)
        
        avg_improvement = sum(improvements) / len(improvements) if improvements else 0.0
        
        return {
            "total_rounds": len(self.rounds),
            "current_round": self.current_round.round_number if self.current_round else 0,
            "total_hospitals": total_hospitals,
            "active_hospitals": active_hospitals,
            "average_accuracy_improvement": avg_improvement,
            "hospitals": [
                {
                    "hospital_id": h.hospital_id,
                    "local_accuracy": h.local_accuracy,
                    "global_accuracy": h.global_accuracy,
                    "improvement": h.global_accuracy - h.local_accuracy,
                    "gradients_uploaded": h.total_gradients_uploaded,
                    "models_downloaded": h.total_models_downloaded,
                    "last_active": h.last_gradient_upload.isoformat() if h.last_gradient_upload else None
                }
                for h in self.hospitals.values()
            ],
            "rounds": [
                {
                    "round": r.round_number,
                    "start": r.start_time.isoformat(),
                    "end": r.end_time.isoformat() if r.end_time else None,
                    "hospitals": len(r.participating_hospitals),
                    "status": r.status
                }
                for r in self.rounds[-10:]  # Last 10 rounds
            ]
        }
    
    
    async def scheduled_training_loop(self, interval_hours: int = 168):
        """
        Automatic scheduled training rounds
        
        Args:
            interval_hours: Hours between rounds (default 168 = 1 week)
        """
        logger.info(f"Starting scheduled federated training (every {interval_hours} hours)")
        
        while True:
            try:
                # Wait for interval
                await asyncio.sleep(interval_hours * 3600)
                
                # Sync with database to get newly registered hospitals
                self.sync_with_db()
                
                # Check if we have enough hospitals
                active_hospitals = [h for h in self.hospitals.values() if h.is_active]
                
                if len(active_hospitals) < self.min_hospitals:
                    logger.warning(
                        f"Not enough active hospitals ({len(active_hospitals)}/{self.min_hospitals}). "
                        f"Skipping scheduled round."
                    )
                    continue
                
                # Start new round
                logger.info("Starting scheduled federated training round")
                self.start_new_round()
                
                # Notify hospitals to start training
                await self._notify_hospitals_training_start()
                
            except Exception as e:
                logger.error(f"Scheduled training error: {e}", exc_info=True)
    
    
    async def _notify_hospitals_training_start(self):
        """Notify hospitals to start local training and upload gradients"""
        logger.info(f"Notifying hospitals: training round {self.current_round.round_number} starting")
        
        # In production:
        # - Send email/push notifications
        # - Update hospital dashboards
        # - Auto-trigger training on configured hospitals


# Global singleton
_federated_manager: Optional[FederatedModelManager] = None


def get_federated_manager() -> FederatedModelManager:
    """Get global federated model manager"""
    global _federated_manager
    if _federated_manager is None:
        _federated_manager = FederatedModelManager()
        _federated_manager.start_new_round()
    return _federated_manager


def initialize_federated_manager(**kwargs) -> FederatedModelManager:
    """Initialize federated manager with custom config"""
    global _federated_manager
    _federated_manager = FederatedModelManager(**kwargs)
    _federated_manager.start_new_round()
    return _federated_manager
