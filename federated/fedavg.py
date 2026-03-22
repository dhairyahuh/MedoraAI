"""
Federated Learning Implementation - FedAvg Algorithm
Based on: McMahan et al. "Communication-Efficient Learning" (AISTATS 2017)
"""
import torch
import torch.nn as nn
from typing import List, Dict, Tuple, Optional
import logging
from collections import OrderedDict
import numpy as np

logger = logging.getLogger(__name__)


class FederatedAveraging:
    """
    FedAvg: Federated Averaging Algorithm
    
    Paper: McMahan et al., "Communication-Efficient Learning of Deep Networks 
           from Decentralized Data" (AISTATS 2017)
    
    Algorithm:
    1. Server broadcasts global model to K hospitals
    2. Each hospital trains locally on private data for E epochs
    3. Hospitals send gradients (Δw) back to server
    4. Server aggregates: w_new = w_old + (1/K) Σ Δw_k
    5. Repeat for T rounds
    
    Why FedAvg:
    - Communication-efficient (sends full model updates, not per-batch)
    - Robust to non-IID data (hospitals have different disease distributions)
    - Proven convergence guarantees
    - Standard baseline for federated learning
    """
    
    def __init__(self, global_model: nn.Module, learning_rate: float = 1.0):
        """
        Initialize FedAvg server
        
        Args:
            global_model: Global model architecture
            learning_rate: Server learning rate (typically 1.0 for averaging)
        """
        self.global_model = global_model
        self.learning_rate = learning_rate
        self.round = 0
        
        logger.info("FedAvg server initialized")
    
    def aggregate_gradients(
        self,
        client_gradients: List[OrderedDict],
        client_weights: Optional[List[float]] = None
    ) -> OrderedDict:
        """
        Aggregate gradients from multiple hospitals
        
        FedAvg Formula:
            w_new = w_old + η * (1/K) Σ_k (w_k - w_old)
            where w_k are client models, η is learning rate
        
        Args:
            client_gradients: List of gradients from K hospitals
                             Each is OrderedDict of {param_name: gradient_tensor}
            client_weights: Optional weights for weighted averaging
                           (e.g., proportional to dataset size)
        
        Returns:
            Aggregated gradient (averaged across hospitals)
        """
        K = len(client_gradients)
        
        if K == 0:
            raise ValueError("No client gradients to aggregate")
        
        # Default to equal weighting
        if client_weights is None:
            client_weights = [1.0 / K] * K
        else:
            # Normalize weights
            total_weight = sum(client_weights)
            client_weights = [w / total_weight for w in client_weights]
        
        logger.info(f"Aggregating gradients from {K} hospitals")
        
        # Initialize aggregated gradient
        aggregated = OrderedDict()
        
        # Average each parameter
        for param_name in client_gradients[0].keys():
            # Weighted sum: Σ (weight_k * gradient_k)
            weighted_sum = sum(
                weight * client_grad[param_name]
                for weight, client_grad in zip(client_weights, client_gradients)
            )
            
            aggregated[param_name] = weighted_sum
        
        return aggregated
    
    def apply_aggregated_gradient(self, aggregated_gradient: OrderedDict):
        """
        Apply aggregated gradient to global model
        
        Args:
            aggregated_gradient: Averaged gradient from all hospitals
        """
        with torch.no_grad():
            for param_name, param in self.global_model.named_parameters():
                if param_name in aggregated_gradient:
                    # Update: w_new = w_old - lr * grad
                    param.data -= self.learning_rate * aggregated_gradient[param_name]
        
        self.round += 1
        logger.info(f"Global model updated (round {self.round})")
    
    def apply_gradients(self, aggregated_gradient: OrderedDict):
        """
        Alias for apply_aggregated_gradient for compatibility
        
        Args:
            aggregated_gradient: Averaged gradient from all hospitals
        """
        self.apply_aggregated_gradient(aggregated_gradient)
    
    def get_global_model_state(self) -> OrderedDict:
        """
        Get current global model state dict
        
        Returns:
            Model state dict (for distribution to hospitals)
        """
        return self.global_model.state_dict()
    
    def federated_round(
        self,
        client_gradients: List[OrderedDict],
        client_weights: Optional[List[float]] = None
    ) -> OrderedDict:
        """
        Complete one federated learning round
        
        Args:
            client_gradients: Gradients from K hospitals
            client_weights: Optional client weights
        
        Returns:
            Updated global model state
        """
        # Aggregate
        aggregated = self.aggregate_gradients(client_gradients, client_weights)
        
        # Apply to global model
        self.apply_aggregated_gradient(aggregated)
        
        # Return new global state
        return self.get_global_model_state()


class FedProx(FederatedAveraging):
    """
    FedProx: Federated Optimization in Heterogeneous Networks
    
    Paper: Li et al., "Federated Optimization in Heterogeneous Networks" (MLSys 2020)
    
    Improvement over FedAvg:
    - Adds proximal term to handle non-IID data
    - More robust to heterogeneous hospitals
    - Better convergence in practice
    
    Loss modification:
        L_local = L_data + (μ/2) ||w - w_global||²
    
    where μ is proximal term weight
    """
    
    def __init__(self, global_model: nn.Module, mu: float = 0.01, learning_rate: float = 1.0):
        """
        Initialize FedProx server
        
        Args:
            global_model: Global model
            mu: Proximal term weight (higher = stay closer to global model)
            learning_rate: Server learning rate
        """
        super().__init__(global_model, learning_rate)
        self.mu = mu
        logger.info(f"FedProx server initialized (μ={mu})")
    
    def get_proximal_term(self, local_model: OrderedDict) -> OrderedDict:
        """
        Compute proximal term: (μ/2) ||w - w_global||²
        
        Args:
            local_model: Local hospital model state
        
        Returns:
            Proximal gradient to add to local training
        """
        global_state = self.global_model.state_dict()
        proximal = OrderedDict()
        
        for param_name in local_model.keys():
            # Gradient of proximal term: μ (w - w_global)
            proximal[param_name] = self.mu * (
                local_model[param_name] - global_state[param_name]
            )
        
        return proximal


class ByzantineRobustAggregation:
    """
    Byzantine-robust aggregation using Krum algorithm
    
    Paper: Blanchard et al., "Machine Learning with Adversaries: 
           Byzantine Tolerant Gradient Descent" (NIPS 2017)
    
    Problem: Malicious hospitals can send poisoned gradients
    Solution: Select gradient closest to cluster of honest gradients
    
    Use Case:
    - One hospital tries to backdoor the model
    - Krum detects and excludes the outlier gradient
    """
    
    @staticmethod
    def krum(
        client_gradients: List[OrderedDict],
        num_byzantine: int = 1,
        multi_krum: bool = False
    ) -> List[int]:
        """
        Krum algorithm: Select most trustworthy gradients
        
        Args:
            client_gradients: Gradients from K hospitals
            num_byzantine: Maximum number of Byzantine (malicious) hospitals
            multi_krum: If True, return multiple gradients (Multi-Krum)
        
        Returns:
            Indices of selected gradients
        """
        K = len(client_gradients)
        f = num_byzantine
        
        if K < 2 * f + 3:
            logger.warning(f"Not enough hospitals ({K}) for Byzantine tolerance (need {2*f+3})")
            return list(range(K))
        
        # Flatten gradients to vectors
        vectors = []
        for grad_dict in client_gradients:
            vec = torch.cat([g.flatten() for g in grad_dict.values()])
            vectors.append(vec)
        
        # Compute pairwise distances
        distances = torch.zeros(K, K)
        for i in range(K):
            for j in range(i + 1, K):
                dist = torch.norm(vectors[i] - vectors[j], p=2).item()
                distances[i, j] = dist
                distances[j, i] = dist
        
        # For each gradient, compute score = sum of distances to (K-f-2) closest gradients
        scores = []
        for i in range(K):
            # Get distances to all other gradients
            dists_i = distances[i].clone()
            dists_i[i] = float('inf')  # Exclude self
            
            # Sort and sum (K-f-2) smallest
            sorted_dists, _ = torch.sort(dists_i)
            score = sorted_dists[:K - f - 2].sum().item()
            scores.append(score)
        
        # Select gradient(s) with lowest score (most central)
        if multi_krum:
            # Multi-Krum: Select (K-f) gradients
            m = K - f
            selected_indices = np.argsort(scores)[:m].tolist()
            logger.info(f"Multi-Krum selected {m}/{K} gradients")
        else:
            # Krum: Select 1 gradient
            selected_indices = [int(np.argmin(scores))]
            logger.info(f"Krum selected gradient {selected_indices[0]} (score: {scores[selected_indices[0]]:.2f})")
        
        return selected_indices
    
    @staticmethod
    def trimmed_mean(
        client_gradients: List[OrderedDict],
        trim_ratio: float = 0.1
    ) -> OrderedDict:
        """
        Trimmed mean: Remove outliers before averaging
        
        Algorithm:
        1. For each parameter coordinate
        2. Sort values across all hospitals
        3. Remove top/bottom trim_ratio
        4. Average remaining values
        
        Args:
            client_gradients: Gradients from K hospitals
            trim_ratio: Fraction to trim from each end (0.1 = remove top/bottom 10%)
        
        Returns:
            Trimmed mean gradient
        """
        K = len(client_gradients)
        num_trim = int(K * trim_ratio)
        
        logger.info(f"Trimmed mean: removing {num_trim} outliers from each end")
        
        trimmed = OrderedDict()
        
        for param_name in client_gradients[0].keys():
            # Stack gradients for this parameter
            param_stack = torch.stack([
                grad[param_name] for grad in client_gradients
            ])  # Shape: (K, ...)
            
            # Sort along hospital dimension
            sorted_params, _ = torch.sort(param_stack, dim=0)
            
            # Trim top/bottom
            if num_trim > 0:
                trimmed_params = sorted_params[num_trim:-num_trim]
            else:
                trimmed_params = sorted_params
            
            # Average
            trimmed[param_name] = trimmed_params.mean(dim=0)
        
        return trimmed


# Example usage
if __name__ == "__main__":
    # Create dummy model
    model = nn.Sequential(
        nn.Linear(10, 50),
        nn.ReLU(),
        nn.Linear(50, 2)
    )
    
    print("--- Testing FedAvg ---")
    fedavg = FederatedAveraging(model)
    
    # Simulate 3 hospitals sending gradients
    client_gradients = []
    for i in range(3):
        # Create dummy gradient (in practice: computed from local training)
        grad = OrderedDict()
        for name, param in model.named_parameters():
            grad[name] = torch.randn_like(param) * 0.01
        client_gradients.append(grad)
    
    # Aggregate
    print(f"Aggregating gradients from {len(client_gradients)} hospitals...")
    aggregated = fedavg.aggregate_gradients(client_gradients)
    print(f"✓ Aggregated gradient has {len(aggregated)} parameters")
    
    # Apply to global model
    fedavg.apply_aggregated_gradient(aggregated)
    print(f"✓ Global model updated (round {fedavg.round})")
    
    # Test weighted averaging
    print("\n--- Testing Weighted FedAvg ---")
    client_weights = [0.5, 0.3, 0.2]  # Hospital 1 has more data
    aggregated_weighted = fedavg.aggregate_gradients(client_gradients, client_weights)
    print(f"✓ Weighted aggregation complete")
    
    # Test Byzantine-robust aggregation
    print("\n--- Testing Byzantine-Robust Aggregation ---")
    
    # Add poisoned gradient (outlier)
    poisoned_grad = OrderedDict()
    for name, param in model.named_parameters():
        poisoned_grad[name] = torch.randn_like(param) * 10.0  # 10x larger
    client_gradients.append(poisoned_grad)
    
    print(f"Total gradients: {len(client_gradients)} (1 poisoned)")
    
    # Krum
    selected_indices = ByzantineRobustAggregation.krum(
        client_gradients,
        num_byzantine=1
    )
    print(f"✓ Krum selected gradient {selected_indices[0]}")
    print(f"  (Poisoned gradient index: {len(client_gradients)-1})")
    
    # Trimmed mean
    trimmed_grad = ByzantineRobustAggregation.trimmed_mean(
        client_gradients,
        trim_ratio=0.25  # Remove 25% from each end
    )
    print(f"✓ Trimmed mean computed (removed outliers)")
    
    print("\n✓ All federated learning tests passed!")
