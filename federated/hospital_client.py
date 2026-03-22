"""
Hospital-side client for federated learning
Downloads global models and uses them for inference
"""
import logging
import torch
import torch.nn as nn
from pathlib import Path
from typing import Optional, Dict
import requests
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class HospitalFederatedClient:
    """
    Hospital-side federated learning client
    - Downloads global model from central server
    - Uses global model for predictions
    - Trains on local data and uploads gradients
    - Tracks local vs global performance
    """
    
    def __init__(
        self,
        hospital_id: str,
        central_server_url: str,
        auth_token: str,
        model_dir: Path = Path("models/federated/hospital")
    ):
        self.hospital_id = hospital_id
        self.central_server_url = central_server_url.rstrip('/')
        self.auth_token = auth_token
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Local and global models
        self.local_model: Optional[nn.Module] = None
        self.global_model: Optional[nn.Module] = None
        self.current_global_round: int = 0
        
        # Performance tracking
        self.local_accuracy: float = 0.0
        self.global_accuracy: float = 0.0
        
        # Use global model by default
        self.use_global_model: bool = True
        
        logger.info(f"HospitalFederatedClient initialized for {hospital_id}")
    
    
    def get_active_model(self) -> Optional[nn.Module]:
        """
        Get the model to use for predictions
        
        Returns global model if available and enabled, otherwise local model
        """
        if self.use_global_model and self.global_model is not None:
            return self.global_model
        return self.local_model
    
    
    async def download_global_model(self) -> bool:
        """
        Download latest global model from central server
        
        Returns:
            True if download successful, False otherwise
        """
        try:
            url = f"{self.central_server_url}/api/v1/federated/download_model"
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            logger.info(f"Downloading global model from {url}")
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to download global model: {response.status_code} {response.text}")
                return False
            
            # Get round number from headers
            round_num = int(response.headers.get('X-Model-Round', 0))
            
            # Save encrypted model
            encrypted_path = self.model_dir / f"global_model_round_{round_num}.enc"
            with open(encrypted_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded global model (round {round_num}, {len(response.content)} bytes)")
            
            # Decrypt and load model
            # In production: use crypto_handler to decrypt
            # For now, assume decrypted
            model_path = self.model_dir / f"global_model_round_{round_num}.pth"
            # TODO: decrypt encrypted_path -> model_path
            
            # Load global model
            if model_path.exists():
                self.global_model = self._load_model(model_path)
                self.current_global_round = round_num
                
                logger.info(f"✓ Global model loaded (round {round_num})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error downloading global model: {e}", exc_info=True)
            return False
    
    
    def _load_model(self, model_path: Path) -> nn.Module:
        """Load model from file"""
        # Simple demo model (replace with actual CheXNet)
        model = nn.Sequential(
            nn.Linear(224*224*3, 128),
            nn.ReLU(),
            nn.Linear(128, 14)
        )
        
        state_dict = torch.load(model_path, map_location='cpu')
        model.load_state_dict(state_dict)
        model.eval()
        
        return model
    
    
    def predict(self, image_tensor: torch.Tensor) -> torch.Tensor:
        """
        Make prediction using active model (global or local)
        
        Args:
            image_tensor: Input image tensor [B, C, H, W]
        
        Returns:
            Predictions tensor
        """
        model = self.get_active_model()
        
        if model is None:
            raise RuntimeError("No model available for prediction (download global or train local)")
        
        model.eval()
        with torch.no_grad():
            predictions = model(image_tensor)
        
        return predictions
    
    
    def train_local_model(
        self,
        train_loader,
        epochs: int = 5,
        learning_rate: float = 0.001
    ):
        """
        Train local model on hospital's private data
        
        Args:
            train_loader: DataLoader with local training data
            epochs: Number of training epochs
            learning_rate: Learning rate
        """
        # Initialize local model (start from global if available)
        if self.global_model is not None:
            logger.info("Initializing local model from global model")
            self.local_model = self._copy_model(self.global_model)
        else:
            logger.info("Initializing new local model")
            self.local_model = self._create_new_model()
        
        # Train
        self.local_model.train()
        optimizer = torch.optim.Adam(self.local_model.parameters(), lr=learning_rate)
        criterion = nn.BCEWithLogitsLoss()
        
        logger.info(f"Training local model for {epochs} epochs on {len(train_loader)} batches")
        
        for epoch in range(epochs):
            total_loss = 0.0
            for batch_idx, (images, labels) in enumerate(train_loader):
                optimizer.zero_grad()
                
                outputs = self.local_model(images)
                loss = criterion(outputs, labels)
                
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            avg_loss = total_loss / len(train_loader)
            logger.info(f"Epoch {epoch+1}/{epochs}: Loss = {avg_loss:.4f}")
        
        logger.info("✓ Local model training complete")
    
    
    def _copy_model(self, model: nn.Module) -> nn.Module:
        """Create a copy of a model"""
        new_model = self._create_new_model()
        new_model.load_state_dict(model.state_dict())
        return new_model
    
    
    def _create_new_model(self) -> nn.Module:
        """Create new model architecture"""
        return nn.Sequential(
            nn.Linear(224*224*3, 128),
            nn.ReLU(),
            nn.Linear(128, 14)
        )
    
    
    def evaluate_model(self, test_loader, model: Optional[nn.Module] = None) -> float:
        """
        Evaluate model accuracy
        
        Args:
            test_loader: DataLoader with test data
            model: Model to evaluate (default: active model)
        
        Returns:
            Accuracy (0.0 to 1.0)
        """
        if model is None:
            model = self.get_active_model()
        
        if model is None:
            return 0.0
        
        model.eval()
        correct = 0
        total = 0
        
        with torch.no_grad():
            for images, labels in test_loader:
                outputs = model(images)
                predictions = torch.sigmoid(outputs) > 0.5
                
                correct += (predictions == labels).sum().item()
                total += labels.numel()
        
        accuracy = correct / total if total > 0 else 0.0
        return accuracy
    
    
    def compare_models(self, test_loader) -> Dict[str, float]:
        """
        Compare local model vs global model performance
        
        Returns:
            Dict with local_accuracy, global_accuracy, improvement
        """
        logger.info("Comparing local vs global model performance")
        
        # Evaluate local model
        if self.local_model is not None:
            self.local_accuracy = self.evaluate_model(test_loader, self.local_model)
            logger.info(f"Local model accuracy: {self.local_accuracy:.2%}")
        
        # Evaluate global model
        if self.global_model is not None:
            self.global_accuracy = self.evaluate_model(test_loader, self.global_model)
            logger.info(f"Global model accuracy: {self.global_accuracy:.2%}")
        
        improvement = self.global_accuracy - self.local_accuracy
        improvement_pct = (improvement / self.local_accuracy * 100) if self.local_accuracy > 0 else 0
        
        logger.info(f"Improvement: {improvement:+.2%} ({improvement_pct:+.1f}%)")
        
        # Report to central server
        self._report_metrics_to_server()
        
        return {
            "local_accuracy": self.local_accuracy,
            "global_accuracy": self.global_accuracy,
            "improvement": improvement,
            "improvement_percent": improvement_pct
        }
    
    
    def _report_metrics_to_server(self):
        """Report local and global accuracy to central server"""
        try:
            url = f"{self.central_server_url}/api/v1/federated/report_metrics"
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            data = {
                "hospital_id": self.hospital_id,
                "local_accuracy": self.local_accuracy,
                "global_accuracy": self.global_accuracy,
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                logger.info("✓ Metrics reported to central server")
            else:
                logger.warning(f"Failed to report metrics: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error reporting metrics: {e}")
    
    
    def get_gradients(self) -> Dict[str, torch.Tensor]:
        """
        Extract gradients from local model for federated aggregation
        
        Returns:
            Dictionary of parameter gradients
        """
        if self.local_model is None:
            raise RuntimeError("No local model trained")
        
        # Get difference between local and global models
        gradients = {}
        
        local_state = self.local_model.state_dict()
        
        if self.global_model is not None:
            global_state = self.global_model.state_dict()
            
            # Gradient = local_weights - global_weights
            for name, local_param in local_state.items():
                if name in global_state:
                    gradients[name] = local_param - global_state[name]
        else:
            # No global model - use local weights as gradients
            gradients = local_state
        
        return gradients
    
    
    async def upload_gradients(self) -> bool:
        """
        Upload local model gradients to central server
        
        Returns:
            True if upload successful
        """
        try:
            gradients = self.get_gradients()
            
            # TODO: Encrypt gradients
            # In production: use crypto_handler
            
            # Serialize gradients
            buffer = torch.save(gradients)
            
            url = f"{self.central_server_url}/api/v1/federated/upload_gradients"
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            logger.info(f"Uploading gradients to {url}")
            
            files = {"encrypted_file": ("gradients.enc", buffer, "application/octet-stream")}
            response = requests.post(url, headers=headers, files=files, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"✓ Gradients uploaded (round {result['round']}, "
                    f"{result['hospitals_waiting']} hospitals waiting)"
                )
                return True
            else:
                logger.error(f"Failed to upload gradients: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error uploading gradients: {e}", exc_info=True)
            return False
    
    
    async def participate_in_round(self, train_loader, test_loader):
        """
        Complete full federated learning round:
        1. Download global model
        2. Train on local data
        3. Upload gradients
        4. Compare performance
        """
        logger.info(f"=== Starting federated learning round for {self.hospital_id} ===")
        
        # Step 1: Download global model
        logger.info("Step 1: Downloading global model")
        await self.download_global_model()
        
        # Step 2: Train on local data
        logger.info("Step 2: Training on local data")
        self.train_local_model(train_loader)
        
        # Step 3: Upload gradients
        logger.info("Step 3: Uploading gradients to central server")
        await self.upload_gradients()
        
        # Step 4: Compare performance
        logger.info("Step 4: Comparing local vs global performance")
        metrics = self.compare_models(test_loader)
        
        logger.info(f"=== Round complete for {self.hospital_id} ===")
        logger.info(f"Results: Local={metrics['local_accuracy']:.2%}, Global={metrics['global_accuracy']:.2%}, Improvement={metrics['improvement']:+.2%}")
        
        return metrics


# Hospital-specific clients
_hospital_clients: Dict[str, HospitalFederatedClient] = {}


def get_hospital_client(hospital_id: str) -> Optional[HospitalFederatedClient]:
    """Get hospital-specific federated client"""
    return _hospital_clients.get(hospital_id)


def initialize_hospital_client(
    hospital_id: str,
    central_server_url: str,
    auth_token: str
) -> HospitalFederatedClient:
    """Initialize hospital federated client"""
    client = HospitalFederatedClient(
        hospital_id=hospital_id,
        central_server_url=central_server_url,
        auth_token=auth_token
    )
    _hospital_clients[hospital_id] = client
    return client
