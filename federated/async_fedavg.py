"""
Asynchronous Federated Averaging with Knowledge Pool (2024-2025)
Dynamic participation - hospitals don't need to be online simultaneously!

Reference:
- "Dynamic Participation in FL: Benchmarks and Knowledge Pool Plugin" (arXiv:2511.16523, Nov 2025)
- Xie et al., "Asynchronous Federated Optimization" (2019)
- Wang et al., "Adaptive Federated Learning in Resource Constrained Edge Computing" (2020)

Key Innovation:
Traditional FedAvg: Wait for K hospitals to be online → aggregate → update
Async FedAvg: Hospital uploads gradient anytime → Knowledge pool stores → Aggregate when ready

Benefits:
- Hospitals contribute on their own schedule (night shifts, maintenance, etc.)
- No synchronization barriers (no waiting for slow hospitals)
- Better convergence: more frequent updates
- Resilient to hospital dropouts
"""

import torch
from typing import Dict, List, Optional, Tuple, Any
import time
from collections import deque
from dataclasses import dataclass
import logging
import json
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class GradientEntry:
    """
    Represents a gradient contribution from a hospital
    """
    hospital_id: str
    gradient: Dict[str, torch.Tensor]
    num_samples: int
    timestamp: float
    round_number: int
    staleness: int = 0  # How many rounds old
    
    def age_seconds(self) -> float:
        """Get age of gradient in seconds"""
        return time.time() - self.timestamp


class KnowledgePool:
    """
    Storage for historical gradients from hospitals
    
    Maintains recent gradients and computes exponential moving average
    for smooth asynchronous aggregation
    """
    
    def __init__(
        self,
        max_pool_size: int = 100,
        max_staleness: int = 5,
        decay_factor: float = 0.9
    ):
        """
        Args:
            max_pool_size: Maximum gradients to store
            max_staleness: Maximum age (in rounds) for a gradient
            decay_factor: Weight decay for old gradients
        """
        self.max_pool_size = max_pool_size
        self.max_staleness = max_staleness
        self.decay_factor = decay_factor
        
        # Storage
        self.pool: deque = deque(maxlen=max_pool_size)
        self.hospital_contributions: Dict[str, int] = {}
        
        # Current global model round
        self.current_round = 0
        
        # Statistics
        self.stats = {
            "total_gradients": 0,
            "active_hospitals": 0,
            "average_staleness": 0.0,
            "aggregations": 0
        }
    
    def add_gradient(
        self,
        hospital_id: str,
        gradient: Dict[str, torch.Tensor],
        num_samples: int
    ) -> int:
        """
        Add a gradient to the knowledge pool
        
        Args:
            hospital_id: Hospital identifier
            gradient: Model gradient
            num_samples: Number of samples used for gradient
        
        Returns:
            Current pool size
        """
        entry = GradientEntry(
            hospital_id=hospital_id,
            gradient=gradient,
            num_samples=num_samples,
            timestamp=time.time(),
            round_number=self.current_round,
            staleness=0
        )
        
        self.pool.append(entry)
        
        # Update hospital contributions
        if hospital_id not in self.hospital_contributions:
            self.hospital_contributions[hospital_id] = 0
        self.hospital_contributions[hospital_id] += 1
        
        # Update stats
        self.stats["total_gradients"] += 1
        self.stats["active_hospitals"] = len(self.hospital_contributions)
        
        logger.info(
            f"Added gradient from {hospital_id} "
            f"(pool size: {len(self.pool)}/{self.max_pool_size})"
        )
        
        return len(self.pool)
    
    def get_recent_gradients(
        self,
        min_gradients: int = 3,
        max_age_seconds: Optional[float] = None
    ) -> List[GradientEntry]:
        """
        Get recent gradients for aggregation
        
        Args:
            min_gradients: Minimum number of gradients required
            max_age_seconds: Maximum age in seconds (None = no limit)
        
        Returns:
            List of recent gradient entries
        """
        if len(self.pool) < min_gradients:
            return []
        
        # Filter by age if specified
        recent = []
        for entry in self.pool:
            if max_age_seconds is None or entry.age_seconds() <= max_age_seconds:
                # Update staleness
                entry.staleness = self.current_round - entry.round_number
                
                # Skip if too stale
                if entry.staleness <= self.max_staleness:
                    recent.append(entry)
        
        # Update average staleness
        if recent:
            avg_staleness = sum(e.staleness for e in recent) / len(recent)
            self.stats["average_staleness"] = avg_staleness
        
        return recent
    
    def aggregate_with_decay(
        self,
        gradients: List[GradientEntry]
    ) -> Tuple[Dict[str, torch.Tensor], Dict[str, float]]:
        """
        Aggregate gradients with staleness-aware weighting
        
        Older gradients get lower weight using exponential decay:
        weight_i = decay_factor^staleness_i * num_samples_i
        
        Args:
            gradients: List of gradient entries
        
        Returns:
            (aggregated_gradient, metadata)
        """
        if not gradients:
            raise ValueError("No gradients to aggregate")
        
        # Calculate weights with staleness decay
        weights = []
        for entry in gradients:
            # Base weight by sample count
            base_weight = entry.num_samples
            
            # Decay by staleness
            staleness_weight = self.decay_factor ** entry.staleness
            
            # Combined weight
            weight = base_weight * staleness_weight
            weights.append(weight)
        
        # Normalize weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        # Weighted aggregation
        aggregated = {}
        first_gradient = gradients[0].gradient
        
        for key in first_gradient.keys():
            aggregated[key] = sum(
                w * entry.gradient[key]
                for w, entry in zip(normalized_weights, gradients)
            )
        
        # Metadata
        metadata = {
            "num_gradients": len(gradients),
            "total_samples": sum(e.num_samples for e in gradients),
            "avg_staleness": sum(e.staleness for e in gradients) / len(gradients),
            "hospitals": list(set(e.hospital_id for e in gradients))
        }
        
        logger.info(
            f"Aggregated {len(gradients)} gradients "
            f"(avg staleness: {metadata['avg_staleness']:.1f})"
        )
        
        return aggregated, metadata
    
    def increment_round(self):
        """Increment global round counter"""
        self.current_round += 1
        self.stats["aggregations"] += 1
    
    def clear_stale_gradients(self):
        """Remove gradients older than max_staleness"""
        current_size = len(self.pool)
        
        # Filter out stale gradients
        self.pool = deque(
            (entry for entry in self.pool 
             if self.current_round - entry.round_number <= self.max_staleness),
            maxlen=self.max_pool_size
        )
        
        removed = current_size - len(self.pool)
        if removed > 0:
            logger.info(f"Removed {removed} stale gradients from pool")
    
    def get_statistics(self) -> Dict:
        """Get knowledge pool statistics"""
        return {
            **self.stats,
            "current_round": self.current_round,
            "pool_size": len(self.pool),
            "pool_capacity": self.max_pool_size
        }


class AsyncFedAvgManager:
    """
    Manages asynchronous federated averaging with knowledge pool
    
    Features:
    - Hospitals upload gradients anytime (no synchronization)
    - Knowledge pool stores recent gradients
    - Periodic aggregation when enough gradients available
    - Staleness-aware weighting
    - Compatible with existing security (DP, encryption)
    """
    
    def __init__(
        self,
        min_hospitals: int = 3,
        max_staleness: int = 5,
        aggregation_frequency: float = 60.0,  # seconds
        pool_size: int = 100,
        decay_factor: float = 0.9
    ):
        """
        Args:
            min_hospitals: Minimum gradients before aggregation
            max_staleness: Maximum age (rounds) for gradients
            aggregation_frequency: Time between aggregations (seconds)
            pool_size: Maximum knowledge pool size
            decay_factor: Decay factor for stale gradients
        """
        self.min_hospitals = min_hospitals
        self.max_staleness = max_staleness
        self.aggregation_frequency = aggregation_frequency
        
        # Initialize knowledge pool
        self.knowledge_pool = KnowledgePool(
            max_pool_size=pool_size,
            max_staleness=max_staleness,
            decay_factor=decay_factor
        )
        
        # Timing
        self.last_aggregation_time = time.time()
        
        # Global model state
        self.global_model_state: Optional[Dict[str, torch.Tensor]] = None
        
        logger.info("Asynchronous FedAvg Manager initialized:")
        logger.info(f"  Min hospitals: {min_hospitals}")
        logger.info(f"  Max staleness: {max_staleness} rounds")
        logger.info(f"  Aggregation frequency: {aggregation_frequency}s")
    
    def submit_gradient(
        self,
        hospital_id: str,
        gradient: Dict[str, torch.Tensor],
        num_samples: int
    ) -> Dict[str, Any]:
        """
        Hospital submits gradient asynchronously
        
        Args:
            hospital_id: Hospital identifier
            gradient: Model gradient
            num_samples: Number of samples
        
        Returns:
            Response dict with status and metadata
        """
        # Add to knowledge pool
        pool_size = self.knowledge_pool.add_gradient(
            hospital_id, gradient, num_samples
        )
        
        # Check if aggregation should be triggered
        should_aggregate = self._should_aggregate()
        
        response = {
            "status": "accepted",
            "hospital_id": hospital_id,
            "pool_size": pool_size,
            "current_round": self.knowledge_pool.current_round,
            "next_aggregation": should_aggregate
        }
        
        # Trigger aggregation if conditions met
        if should_aggregate:
            try:
                agg_result = self.aggregate_and_update()
                response["aggregation"] = agg_result
            except Exception as e:
                logger.error(f"Aggregation failed: {e}")
        
        return response
    
    def _should_aggregate(self) -> bool:
        """
        Determine if aggregation should be triggered
        
        Returns:
            True if ready to aggregate
        """
        # Check minimum gradients
        pool_size = len(self.knowledge_pool.pool)
        if pool_size < self.min_hospitals:
            return False
        
        # Check time since last aggregation
        time_since_last = time.time() - self.last_aggregation_time
        if time_since_last < self.aggregation_frequency:
            return False
        
        return True
    
    def aggregate_and_update(self) -> Dict[str, Any]:
        """
        Perform asynchronous aggregation and update global model
        
        Returns:
            Aggregation result metadata
        """
        # Get recent gradients
        recent_gradients = self.knowledge_pool.get_recent_gradients(
            min_gradients=self.min_hospitals
        )
        
        if not recent_gradients:
            logger.warning("Not enough recent gradients for aggregation")
            return {"status": "insufficient_gradients"}
        
        # Aggregate with staleness decay
        aggregated_gradient, metadata = self.knowledge_pool.aggregate_with_decay(
            recent_gradients
        )
        
        # Update global model (in practice, apply to actual model)
        self.global_model_state = aggregated_gradient
        
        # Increment round
        self.knowledge_pool.increment_round()
        
        # Clear stale gradients
        self.knowledge_pool.clear_stale_gradients()
        
        # Update timing
        self.last_aggregation_time = time.time()
        
        result = {
            "status": "success",
            "round": self.knowledge_pool.current_round,
            **metadata
        }
        
        logger.info(
            f"✅ Async aggregation complete (Round {result['round']})"
        )
        
        return result
    
    def get_global_model(self) -> Optional[Dict[str, torch.Tensor]]:
        """
        Get current global model state
        
        Returns:
            Global model state dict
        """
        return self.global_model_state
    
    def get_statistics(self) -> Dict:
        """Get system statistics"""
        return {
            **self.knowledge_pool.get_statistics(),
            "last_aggregation": time.time() - self.last_aggregation_time,
            "aggregation_frequency": self.aggregation_frequency
        }
    
    def force_aggregation(self) -> Dict[str, Any]:
        """Force immediate aggregation regardless of conditions"""
        logger.info("Forcing aggregation...")
        return self.aggregate_and_update()


def create_async_fedavg_manager(
    min_hospitals: int = 3,
    aggregation_interval: float = 60.0
) -> AsyncFedAvgManager:
    """
    Factory function to create async FedAvg manager
    
    Args:
        min_hospitals: Minimum gradients before aggregation
        aggregation_interval: Time between aggregations (seconds)
    
    Returns:
        Configured AsyncFedAvgManager
    """
    manager = AsyncFedAvgManager(
        min_hospitals=min_hospitals,
        max_staleness=5,
        aggregation_frequency=aggregation_interval,
        pool_size=100,
        decay_factor=0.9
    )
    
    logger.info("✅ Asynchronous FedAvg enabled!")
    logger.info("   Hospitals can contribute anytime (no sync needed)")
    
    return manager


if __name__ == "__main__":
    # Demo: Async FedAvg with 5 hospitals
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Asynchronous Federated Averaging Demo")
    print("=" * 60)
    
    # Create manager
    manager = create_async_fedavg_manager(
        min_hospitals=3,
        aggregation_interval=10.0  # 10 seconds for demo
    )
    
    # Simulate hospitals contributing at different times
    hospitals = ["hospital_001", "hospital_002", "hospital_003", 
                 "hospital_004", "hospital_005"]
    
    print("\n📊 Simulating asynchronous contributions...")
    
    for i, hospital_id in enumerate(hospitals):
        # Simulate gradient (dummy data)
        gradient = {
            "layer1.weight": torch.randn(64, 3, 7, 7),
            "layer1.bias": torch.randn(64)
        }
        
        # Submit gradient
        response = manager.submit_gradient(
            hospital_id=hospital_id,
            gradient=gradient,
            num_samples=500 + i * 100
        )
        
        print(f"\n  {hospital_id}: {response['status']}")
        print(f"    Pool size: {response['pool_size']}")
        print(f"    Round: {response['current_round']}")
        
        # Simulate time delay (hospitals contribute at different times)
        time.sleep(0.5)
    
    # Force aggregation
    print("\n🔄 Forcing aggregation...")
    result = manager.force_aggregation()
    
    print(f"\n✅ Async FedAvg Demo Complete!")
    print(f"   Aggregated {result['num_gradients']} gradients")
    print(f"   From {len(result['hospitals'])} hospitals")
    print(f"   Average staleness: {result['avg_staleness']:.2f} rounds")
    
    # Show statistics
    stats = manager.get_statistics()
    print(f"\n📈 Statistics:")
    print(f"   Total gradients: {stats['total_gradients']}")
    print(f"   Active hospitals: {stats['active_hospitals']}")
    print(f"   Aggregations: {stats['aggregations']}")
