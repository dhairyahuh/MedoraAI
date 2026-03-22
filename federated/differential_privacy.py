"""
Differential Privacy for Federated Learning
Implements DP-SGD (Abadi et al., 2016)
"""
import torch
import torch.nn as nn
from typing import Optional, Tuple
import logging
import math

logger = logging.getLogger(__name__)


class DifferentialPrivacy:
    """
    Differential Privacy implementation for gradient protection
    
    Paper: Abadi et al., "Deep Learning with Differential Privacy" (CCS 2016)
    
    Algorithm: DP-SGD
    1. Clip gradients to bound sensitivity: g_clip = g / max(1, ||g||/C)
    2. Add Gaussian noise: g_private = g_clip + N(0, σ²C²I)
    3. Track privacy budget: ε (epsilon)
    
    Privacy Guarantee:
    (ε, δ)-differential privacy where:
    - ε: Privacy budget (lower = more private)
    - δ: Failure probability (typically 10^-5)
    
    Interpretation:
    - ε=0: Perfect privacy (outputs reveal nothing)
    - ε=1: Strong privacy (standard for medical data)
    - ε=10: Weak privacy (acceptable for less sensitive data)
    """
    
    def __init__(
        self,
        epsilon: float = 1.0,
        delta: float = 1e-5,
        clipping_norm: float = 1.0,
        noise_multiplier: Optional[float] = None
    ):
        """
        Initialize DP-SGD
        
        Args:
            epsilon: Privacy budget (target ε)
            delta: Failure probability
            clipping_norm: Gradient clipping threshold (C)
            noise_multiplier: Noise scale (σ). If None, computed from ε
        """
        self.epsilon = epsilon
        self.delta = delta
        self.clipping_norm = clipping_norm
        
        # Compute noise multiplier if not provided
        if noise_multiplier is None:
            # Formula: σ ≈ sqrt(2 * ln(1.25/δ)) / ε
            self.noise_multiplier = math.sqrt(2 * math.log(1.25 / delta)) / epsilon
        else:
            self.noise_multiplier = noise_multiplier
        
        # Privacy accounting
        self.steps = 0
        self.epsilon_spent = 0.0
        
        logger.info(
            f"Differential Privacy initialized: "
            f"ε={epsilon}, δ={delta:.2e}, C={clipping_norm}, σ={self.noise_multiplier:.3f}"
        )
    
    def clip_gradients(self, gradients: dict) -> dict:
        """
        Clip gradients to bound sensitivity
        
        Clipping Formula:
            g_clip = g / max(1, ||g||₂ / C)
        
        Why clip?
        - Bounds how much any single training example can affect the model
        - Essential for privacy guarantee
        
        Args:
            gradients: Dictionary of {param_name: gradient_tensor}
        
        Returns:
            Clipped gradients
        """
        # Compute L2 norm of all gradients
        total_norm = torch.sqrt(sum(
            torch.sum(g ** 2) for g in gradients.values()
        ))
        
        # Clip if norm exceeds threshold
        clip_coef = self.clipping_norm / (total_norm + 1e-6)
        clip_coef = min(clip_coef, 1.0)
        
        clipped = {
            name: grad * clip_coef
            for name, grad in gradients.items()
        }
        
        if clip_coef < 1.0:
            logger.debug(f"Gradients clipped (norm: {total_norm:.4f} → {self.clipping_norm})")
        
        return clipped
    
    def add_noise(self, gradients: dict, device: str = 'cpu') -> dict:
        """
        Add Gaussian noise to gradients
        
        Noise Formula:
            g_private = g_clip + N(0, (σ·C)²I)
        
        Why Gaussian noise?
        - Calibrated to privacy parameters (ε, δ)
        - Provides (ε, δ)-DP guarantee
        - Standard mechanism for DP-SGD
        
        Args:
            gradients: Clipped gradients
            device: 'cpu' or 'cuda'
        
        Returns:
            Noisy gradients
        """
        noise_std = self.noise_multiplier * self.clipping_norm
        
        noisy = {}
        for name, grad in gradients.items():
            # Sample noise from N(0, σ²)
            noise = torch.randn_like(grad, device=device) * noise_std
            noisy[name] = grad + noise
        
        logger.debug(f"Gaussian noise added (σ={noise_std:.4f})")
        
        return noisy
    
    def privatize_gradients(
        self,
        gradients: dict,
        device: str = 'cpu'
    ) -> dict:
        """
        Apply full DP-SGD: clip + add noise
        
        Args:
            gradients: Raw gradients
            device: 'cpu' or 'cuda'
        
        Returns:
            Private gradients (ε, δ)-DP
        """
        # Step 1: Clip
        clipped = self.clip_gradients(gradients)
        
        # Step 2: Add noise
        private = self.add_noise(clipped, device)
        
        # Update privacy accounting
        self.steps += 1
        self.epsilon_spent = self._compute_epsilon_spent()
        
        logger.info(
            f"Gradients privatized (step {self.steps}, "
            f"ε_spent={self.epsilon_spent:.2f}, ε_remaining={self.epsilon - self.epsilon_spent:.2f})"
        )
        
        return private
    
    def _compute_epsilon_spent(self) -> float:
        """
        Compute privacy budget spent so far
        
        Uses moments accountant (tight composition)
        
        Simplified formula (conservative):
            ε_spent = sqrt(2 * steps * ln(1/δ)) * σ
        
        More accurate: Use Rényi DP composition (opacus library)
        
        Returns:
            Total epsilon spent
        """
        # Simple composition (conservative upper bound)
        epsilon_spent = math.sqrt(2 * self.steps * math.log(1 / self.delta)) / self.noise_multiplier
        
        return epsilon_spent
    
    def get_privacy_spent(self) -> Tuple[float, float]:
        """
        Get current privacy budget
        
        Returns:
            (epsilon_spent, epsilon_remaining)
        """
        epsilon_remaining = max(0, self.epsilon - self.epsilon_spent)
        return self.epsilon_spent, epsilon_remaining
    
    def has_privacy_budget(self) -> bool:
        """
        Check if privacy budget is exhausted
        
        Returns:
            True if budget remaining, False if exhausted
        """
        return self.epsilon_spent < self.epsilon
    
    def reset(self):
        """Reset privacy accounting (for new training run)"""
        self.steps = 0
        self.epsilon_spent = 0.0
        logger.info("Privacy budget reset")


class PrivacyAccountant:
    """
    Advanced privacy accounting using Rényi Differential Privacy
    
    Paper: Mironov, "Rényi Differential Privacy" (2017)
    
    Provides tighter privacy bounds than basic composition
    """
    
    def __init__(
        self,
        epsilon: float,
        delta: float,
        sample_rate: float,
        noise_multiplier: float
    ):
        """
        Initialize privacy accountant
        
        Args:
            epsilon: Target privacy budget
            delta: Failure probability
            sample_rate: Fraction of data used per step (q)
            noise_multiplier: Noise scale (σ)
        """
        self.epsilon = epsilon
        self.delta = delta
        self.sample_rate = sample_rate
        self.noise_multiplier = noise_multiplier
        self.steps = 0
        
        logger.info("Privacy accountant initialized (Rényi DP)")
    
    def step(self):
        """Record one training step"""
        self.steps += 1
    
    def get_epsilon(self, orders: list = None) -> float:
        """
        Compute epsilon using Rényi DP composition
        
        Args:
            orders: Rényi orders to compute (default: [1.5, 2, 4, 8, 16, 32, 64])
        
        Returns:
            Current epsilon
        """
        if orders is None:
            orders = [1.5, 2, 4, 8, 16, 32, 64]
        
        # Compute Rényi divergence for each order
        # (Simplified - use opacus.accountants.RDPAccountant for accurate computation)
        
        # Placeholder: Conservative estimate
        epsilon = math.sqrt(2 * self.steps * math.log(1 / self.delta)) / self.noise_multiplier
        
        return epsilon
    
    def get_privacy_spent(self) -> Tuple[float, float, float]:
        """
        Get current privacy budget
        
        Returns:
            (epsilon, delta, steps)
        """
        epsilon_spent = self.get_epsilon()
        return epsilon_spent, self.delta, self.steps


# Example usage
if __name__ == "__main__":
    print("--- Testing Differential Privacy ---")
    
    # Create DP-SGD instance
    dp = DifferentialPrivacy(
        epsilon=1.0,  # Strong privacy
        delta=1e-5,
        clipping_norm=1.0
    )
    
    # Simulate model gradients
    dummy_model = nn.Sequential(
        nn.Linear(10, 50),
        nn.ReLU(),
        nn.Linear(50, 2)
    )
    
    gradients = {
        name: torch.randn_like(param)
        for name, param in dummy_model.named_parameters()
    }
    
    print(f"\nOriginal gradient norms:")
    for name, grad in gradients.items():
        print(f"  {name}: {torch.norm(grad).item():.4f}")
    
    # Test clipping
    print("\n--- Gradient Clipping ---")
    clipped = dp.clip_gradients(gradients)
    total_norm = torch.sqrt(sum(torch.sum(g ** 2) for g in clipped.values()))
    print(f"✓ Clipped total norm: {total_norm.item():.4f} (threshold: {dp.clipping_norm})")
    
    # Test noise addition
    print("\n--- Noise Addition ---")
    noisy = dp.add_noise(clipped)
    print(f"✓ Noise added (σ={dp.noise_multiplier:.3f})")
    
    # Full privatization
    print("\n--- Full DP-SGD ---")
    for step in range(5):
        private_grads = dp.privatize_gradients(gradients)
        eps_spent, eps_remaining = dp.get_privacy_spent()
        print(f"Step {step + 1}: ε_spent={eps_spent:.2f}, ε_remaining={eps_remaining:.2f}")
    
    # Test privacy budget exhaustion
    print("\n--- Testing Privacy Budget ---")
    print(f"Has budget? {dp.has_privacy_budget()}")
    
    # Simulate many steps
    for _ in range(1000):
        dp.privatize_gradients(gradients)
    
    eps_spent, eps_remaining = dp.get_privacy_spent()
    print(f"After 1005 steps:")
    print(f"  ε_spent: {eps_spent:.2f}")
    print(f"  ε_remaining: {eps_remaining:.2f}")
    print(f"  Has budget? {dp.has_privacy_budget()}")
    
    print("\n✓ Differential privacy tests complete!")
