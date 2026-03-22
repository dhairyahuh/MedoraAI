"""
Automated Model Update System

Provides zero-downtime model deployment with:
- Gradual rollout (canary deployment)
- Automatic rollback on performance degradation
- A/B testing support
- Model versioning and history
- Health checks and validation
"""

import os
import logging
import asyncio
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import numpy as np
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class DeploymentStrategy(Enum):
    """Model deployment strategy"""
    IMMEDIATE = "immediate"  # Replace immediately (risky)
    CANARY = "canary"  # Gradual rollout (safe)
    BLUE_GREEN = "blue_green"  # Two environments (safest)
    A_B_TEST = "a_b_test"  # Compare models side-by-side


class DeploymentStatus(Enum):
    """Deployment status"""
    PENDING = "pending"
    VALIDATING = "validating"
    DEPLOYING = "deploying"
    MONITORING = "monitoring"
    COMPLETE = "complete"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class ModelVersion:
    """Model version metadata"""
    model_name: str
    version: str
    path: Path
    accuracy: float
    deployed_at: Optional[datetime] = None
    deployment_strategy: Optional[str] = None
    traffic_percentage: float = 0.0
    total_inferences: int = 0
    successful_inferences: int = 0
    average_latency: float = 0.0
    status: str = "active"


class ModelUpdateManager:
    """
    Manages automated model updates with safe deployment strategies
    
    Features:
    - Canary deployment (gradual traffic shift)
    - Blue-green deployment (instant switch with rollback)
    - A/B testing (compare models)
    - Automatic validation
    - Performance monitoring
    - Automatic rollback on degradation
    """
    
    def __init__(self):
        self.models_dir = Path("models/weights")
        self.versions_dir = Path("models/versions")
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata_file = self.versions_dir / "versions.json"
        self.active_models: Dict[str, ModelVersion] = {}
        self.candidate_models: Dict[str, ModelVersion] = {}
        
        self._load_metadata()
        
        # Deployment settings
        self.canary_stages = [0.01, 0.05, 0.10, 0.25, 0.50, 1.0]  # Traffic percentages
        self.canary_stage_duration = 300  # 5 minutes per stage
        self.performance_threshold = 0.95  # 95% of baseline performance
        self.error_rate_threshold = 0.05  # 5% error rate
        self.latency_threshold_multiplier = 1.5  # 50% slower than baseline
    
    def _load_metadata(self):
        """Load model version metadata from disk"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    
                    for model_data in data.get('active_models', []):
                        model = ModelVersion(**model_data)
                        model.path = Path(model.path)
                        if model_data.get('deployed_at'):
                            model.deployed_at = datetime.fromisoformat(model_data['deployed_at'])
                        self.active_models[model.model_name] = model
                    
                    for model_data in data.get('candidate_models', []):
                        model = ModelVersion(**model_data)
                        model.path = Path(model.path)
                        self.candidate_models[model.model_name] = model
                    
                    logger.info(f"Loaded {len(self.active_models)} active models")
            except Exception as e:
                logger.error(f"Error loading model metadata: {e}")
    
    def _save_metadata(self):
        """Save model version metadata to disk"""
        try:
            def serialize_model(model: ModelVersion) -> dict:
                data = asdict(model)
                data['path'] = str(model.path)
                if model.deployed_at:
                    data['deployed_at'] = model.deployed_at.isoformat()
                return data
            
            data = {
                'active_models': [serialize_model(m) for m in self.active_models.values()],
                'candidate_models': [serialize_model(m) for m in self.candidate_models.values()],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug("Saved model metadata")
        except Exception as e:
            logger.error(f"Error saving model metadata: {e}")
    
    async def deploy_model(
        self,
        model_name: str,
        model_path: Path,
        version: str,
        strategy: DeploymentStrategy = DeploymentStrategy.CANARY,
        validate: bool = True
    ) -> Tuple[bool, str]:
        """
        Deploy new model version with specified strategy
        
        Args:
            model_name: Name of model
            model_path: Path to new model file
            version: Version identifier
            strategy: Deployment strategy
            validate: Run validation before deployment
        
        Returns:
            (success: bool, message: str)
        """
        try:
            logger.info(f"Starting deployment of {model_name} v{version} with {strategy.value} strategy")
            
            # Step 1: Validate model
            if validate:
                logger.info("Validating new model...")
                is_valid, validation_results = await self._validate_model(model_path, model_name)
                
                if not is_valid:
                    return False, f"Model validation failed: {validation_results}"
                
                accuracy = validation_results.get('accuracy', 0.0)
                logger.info(f"Model validation passed (accuracy: {accuracy:.1%})")
            else:
                accuracy = 0.0
            
            # Step 2: Copy model to versions directory
            version_path = self.versions_dir / model_name / version
            version_path.mkdir(parents=True, exist_ok=True)
            
            dest_path = version_path / model_path.name
            shutil.copy2(model_path, dest_path)
            
            # Step 3: Create model version object
            new_version = ModelVersion(
                model_name=model_name,
                version=version,
                path=dest_path,
                accuracy=accuracy,
                deployed_at=datetime.now(),
                deployment_strategy=strategy.value,
                traffic_percentage=0.0
            )
            
            # Step 4: Deploy based on strategy
            if strategy == DeploymentStrategy.IMMEDIATE:
                success, message = await self._deploy_immediate(new_version)
            elif strategy == DeploymentStrategy.CANARY:
                success, message = await self._deploy_canary(new_version)
            elif strategy == DeploymentStrategy.BLUE_GREEN:
                success, message = await self._deploy_blue_green(new_version)
            elif strategy == DeploymentStrategy.A_B_TEST:
                success, message = await self._deploy_ab_test(new_version)
            else:
                return False, f"Unknown deployment strategy: {strategy}"
            
            if success:
                self.active_models[model_name] = new_version
                self._save_metadata()
            
            return success, message
        
        except Exception as e:
            logger.error(f"Error deploying model: {e}")
            return False, f"Deployment error: {e}"
    
    async def _validate_model(self, model_path: Path, model_name: str) -> Tuple[bool, Dict]:
        """Validate model before deployment"""
        from models.model_validator import ModelValidator
        
        validator = ModelValidator()
        passed, results = validator.validate_model(model_path, model_name)
        
        return passed, results
    
    async def _deploy_immediate(self, new_version: ModelVersion) -> Tuple[bool, str]:
        """Deploy immediately (replace active model)"""
        try:
            # Backup current model
            if new_version.model_name in self.active_models:
                old_version = self.active_models[new_version.model_name]
                backup_path = self.versions_dir / new_version.model_name / "backups" / f"{old_version.version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pth"
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(old_version.path, backup_path)
                logger.info(f"Backed up old model to {backup_path}")
            
            # Copy new model to active location
            active_path = self.models_dir / f"{new_version.model_name}.pth"
            shutil.copy2(new_version.path, active_path)
            
            new_version.traffic_percentage = 1.0
            new_version.status = "active"
            
            logger.info(f"Deployed {new_version.model_name} v{new_version.version} immediately")
            return True, "Model deployed successfully"
        
        except Exception as e:
            logger.error(f"Error in immediate deployment: {e}")
            return False, f"Deployment failed: {e}"
    
    async def _deploy_canary(self, new_version: ModelVersion) -> Tuple[bool, str]:
        """
        Deploy with canary strategy (gradual traffic shift)
        
        Traffic progression: 1% → 5% → 10% → 25% → 50% → 100%
        Each stage runs for 5 minutes with monitoring
        """
        try:
            logger.info(f"Starting canary deployment for {new_version.model_name}")
            
            # Get baseline performance from active model
            baseline = self._get_baseline_performance(new_version.model_name)
            
            # Register as candidate
            self.candidate_models[new_version.model_name] = new_version
            
            # Gradual traffic shift
            for stage_idx, traffic_pct in enumerate(self.canary_stages):
                logger.info(f"Canary stage {stage_idx + 1}/{len(self.canary_stages)}: {traffic_pct:.0%} traffic")
                
                # Update traffic percentage
                new_version.traffic_percentage = traffic_pct
                self._save_metadata()
                
                # Monitor for stage duration
                await asyncio.sleep(self.canary_stage_duration)
                
                # Check performance
                performance = self._get_model_performance(new_version)
                
                # Compare to baseline
                if baseline and performance:
                    if performance['accuracy'] < baseline['accuracy'] * self.performance_threshold:
                        logger.error(f"Canary accuracy degraded: {performance['accuracy']:.1%} < {baseline['accuracy'] * self.performance_threshold:.1%}")
                        await self._rollback(new_version, baseline)
                        return False, "Deployment rolled back due to accuracy degradation"
                    
                    if performance['error_rate'] > self.error_rate_threshold:
                        logger.error(f"Canary error rate too high: {performance['error_rate']:.1%}")
                        await self._rollback(new_version, baseline)
                        return False, "Deployment rolled back due to high error rate"
                    
                    if performance['avg_latency'] > baseline['avg_latency'] * self.latency_threshold_multiplier:
                        logger.error(f"Canary latency too high: {performance['avg_latency']:.3f}s > {baseline['avg_latency'] * self.latency_threshold_multiplier:.3f}s")
                        await self._rollback(new_version, baseline)
                        return False, "Deployment rolled back due to high latency"
                
                logger.info(f"Canary stage {stage_idx + 1} passed: accuracy={performance.get('accuracy', 0):.1%}, latency={performance.get('avg_latency', 0):.3f}s")
            
            # All stages passed - promote to active
            new_version.traffic_percentage = 1.0
            new_version.status = "active"
            self.active_models[new_version.model_name] = new_version
            
            if new_version.model_name in self.candidate_models:
                del self.candidate_models[new_version.model_name]
            
            self._save_metadata()
            
            logger.info(f"Canary deployment complete for {new_version.model_name}")
            return True, "Canary deployment completed successfully"
        
        except Exception as e:
            logger.error(f"Error in canary deployment: {e}")
            await self._rollback(new_version, baseline)
            return False, f"Canary deployment failed: {e}"
    
    async def _deploy_blue_green(self, new_version: ModelVersion) -> Tuple[bool, str]:
        """
        Deploy with blue-green strategy
        
        - Blue: Current active model
        - Green: New model (fully deployed in parallel)
        - Instant switch with quick rollback if needed
        """
        try:
            logger.info(f"Starting blue-green deployment for {new_version.model_name}")
            
            # Deploy "green" environment (new model)
            green_path = self.models_dir / f"{new_version.model_name}_green.pth"
            shutil.copy2(new_version.path, green_path)
            
            # Run health checks on green
            is_healthy, health_message = await self._health_check_model(green_path, new_version.model_name)
            
            if not is_healthy:
                logger.error(f"Green environment health check failed: {health_message}")
                green_path.unlink()
                return False, f"Health check failed: {health_message}"
            
            # Switch traffic to green (instant cutover)
            blue_path = self.models_dir / f"{new_version.model_name}.pth"
            backup_path = self.models_dir / f"{new_version.model_name}_blue_backup.pth"
            
            if blue_path.exists():
                shutil.copy2(blue_path, backup_path)
            
            shutil.copy2(green_path, blue_path)
            
            # Monitor for 1 minute
            logger.info("Monitoring new deployment...")
            await asyncio.sleep(60)
            
            performance = self._get_model_performance(new_version)
            
            # Check if rollback needed
            if performance and performance.get('error_rate', 1.0) > self.error_rate_threshold:
                logger.error("High error rate detected, rolling back")
                if backup_path.exists():
                    shutil.copy2(backup_path, blue_path)
                return False, "Rolled back due to high error rate"
            
            # Success - clean up
            green_path.unlink()
            if backup_path.exists():
                backup_path.unlink()
            
            new_version.traffic_percentage = 1.0
            new_version.status = "active"
            self.active_models[new_version.model_name] = new_version
            self._save_metadata()
            
            logger.info(f"Blue-green deployment complete for {new_version.model_name}")
            return True, "Blue-green deployment completed successfully"
        
        except Exception as e:
            logger.error(f"Error in blue-green deployment: {e}")
            return False, f"Blue-green deployment failed: {e}"
    
    async def _deploy_ab_test(self, new_version: ModelVersion) -> Tuple[bool, str]:
        """
        Deploy with A/B testing strategy
        
        Runs both models in parallel with 50/50 traffic split
        Compares performance over 24 hours
        Promotes better model
        """
        try:
            logger.info(f"Starting A/B test deployment for {new_version.model_name}")
            
            # Register as candidate with 50% traffic
            new_version.traffic_percentage = 0.5
            self.candidate_models[new_version.model_name] = new_version
            self._save_metadata()
            
            # Run A/B test for 24 hours (or configurable duration)
            test_duration = int(os.getenv('AB_TEST_DURATION', '86400'))  # 24 hours default
            logger.info(f"Running A/B test for {test_duration / 3600:.1f} hours")
            
            await asyncio.sleep(test_duration)
            
            # Compare performance
            old_performance = self._get_baseline_performance(new_version.model_name)
            new_performance = self._get_model_performance(new_version)
            
            if not old_performance or not new_performance:
                return False, "Insufficient data to compare models"
            
            # Decide winner based on accuracy and latency
            old_score = old_performance['accuracy'] * (1.0 / max(old_performance['avg_latency'], 0.001))
            new_score = new_performance['accuracy'] * (1.0 / max(new_performance['avg_latency'], 0.001))
            
            if new_score > old_score:
                logger.info(f"New model wins A/B test: {new_score:.3f} vs {old_score:.3f}")
                new_version.traffic_percentage = 1.0
                new_version.status = "active"
                self.active_models[new_version.model_name] = new_version
                
                if new_version.model_name in self.candidate_models:
                    del self.candidate_models[new_version.model_name]
                
                self._save_metadata()
                return True, "A/B test complete - new model promoted"
            else:
                logger.info(f"Old model wins A/B test: {old_score:.3f} vs {new_score:.3f}")
                if new_version.model_name in self.candidate_models:
                    del self.candidate_models[new_version.model_name]
                self._save_metadata()
                return False, "A/B test complete - old model retained"
        
        except Exception as e:
            logger.error(f"Error in A/B test deployment: {e}")
            return False, f"A/B test failed: {e}"
    
    async def _health_check_model(self, model_path: Path, model_name: str) -> Tuple[bool, str]:
        """Run health check on model"""
        try:
            import torch
            
            # Check model loads
            checkpoint = torch.load(model_path, map_location='cpu')
            
            # Check model structure
            if not isinstance(checkpoint, dict):
                return False, "Invalid checkpoint format"
            
            return True, "Model healthy"
        
        except Exception as e:
            return False, f"Health check failed: {e}"
    
    def _get_baseline_performance(self, model_name: str) -> Optional[Dict]:
        """Get performance metrics for active model"""
        if model_name not in self.active_models:
            return None
        
        model = self.active_models[model_name]
        
        return {
            'accuracy': model.accuracy,
            'avg_latency': model.average_latency,
            'error_rate': 1.0 - (model.successful_inferences / max(model.total_inferences, 1)),
            'total_inferences': model.total_inferences
        }
    
    def _get_model_performance(self, model_version: ModelVersion) -> Dict:
        """Get current performance metrics for model"""
        # In production, this would query real-time metrics from monitoring system
        # For now, use model's stored metrics
        return {
            'accuracy': model_version.accuracy,
            'avg_latency': model_version.average_latency,
            'error_rate': 1.0 - (model_version.successful_inferences / max(model_version.total_inferences, 1)),
            'total_inferences': model_version.total_inferences
        }
    
    async def _rollback(self, failed_version: ModelVersion, baseline: Optional[Dict]):
        """Rollback to previous model version"""
        try:
            logger.warning(f"Rolling back {failed_version.model_name} v{failed_version.version}")
            
            failed_version.status = "rolled_back"
            
            if failed_version.model_name in self.candidate_models:
                del self.candidate_models[failed_version.model_name]
            
            # Restore previous model (from backup if exists)
            backup_path = self.models_dir / f"{failed_version.model_name}_blue_backup.pth"
            if backup_path.exists():
                active_path = self.models_dir / f"{failed_version.model_name}.pth"
                shutil.copy2(backup_path, active_path)
                logger.info(f"Restored previous model from backup")
            
            self._save_metadata()
            
            # Send alert
            from api.alert_manager import get_alert_manager
            alert_mgr = get_alert_manager()
            alert_mgr.send_alert(
                'ERROR',
                'model',
                f'Model deployment rolled back: {failed_version.model_name} v{failed_version.version}',
                {'baseline': baseline, 'failed_version': failed_version.version}
            )
        
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
    
    def record_inference(
        self,
        model_name: str,
        success: bool,
        latency: float
    ):
        """Record inference metrics for monitoring"""
        if model_name in self.active_models:
            model = self.active_models[model_name]
            model.total_inferences += 1
            if success:
                model.successful_inferences += 1
            
            # Update rolling average latency
            alpha = 0.1  # Exponential moving average factor
            model.average_latency = alpha * latency + (1 - alpha) * model.average_latency
    
    def get_active_version(self, model_name: str) -> Optional[ModelVersion]:
        """Get currently active model version"""
        return self.active_models.get(model_name)
    
    def list_versions(self, model_name: str) -> List[ModelVersion]:
        """List all versions for a model"""
        versions = []
        model_dir = self.versions_dir / model_name
        
        if model_dir.exists():
            for version_dir in model_dir.iterdir():
                if version_dir.is_dir() and version_dir.name != "backups":
                    versions.append(version_dir.name)
        
        return sorted(versions, reverse=True)
    
    def get_deployment_status(self, model_name: str) -> Dict:
        """Get current deployment status"""
        status = {
            'model_name': model_name,
            'active_version': None,
            'candidate_version': None,
            'deployment_in_progress': False
        }
        
        if model_name in self.active_models:
            status['active_version'] = asdict(self.active_models[model_name])
        
        if model_name in self.candidate_models:
            status['candidate_version'] = asdict(self.candidate_models[model_name])
            status['deployment_in_progress'] = True
        
        return status


# Global instance
_model_update_manager = None


def get_model_update_manager() -> ModelUpdateManager:
    """Get global model update manager instance"""
    global _model_update_manager
    if _model_update_manager is None:
        _model_update_manager = ModelUpdateManager()
    return _model_update_manager


# CLI for testing
if __name__ == '__main__':
    import asyncio
    
    async def test_deployment():
        manager = get_model_update_manager()
        
        # Test canary deployment
        success, message = await manager.deploy_model(
            model_name='pneumonia_detector',
            model_path=Path('models/weights/pneumonia_detector_v2.pth'),
            version='2.0',
            strategy=DeploymentStrategy.CANARY,
            validate=True
        )
        
        print(f"Deployment result: {message}")
        
        if success:
            status = manager.get_deployment_status('pneumonia_detector')
            print(f"Active version: {status['active_version']['version']}")
    
    asyncio.run(test_deployment())
