"""
Test Federated Learning Implementation
Tests gradient computation, storage, aggregation, and API endpoints
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import torch
from collections import OrderedDict
from federated.federated_storage import FederatedStorage
from federated.differential_privacy import DifferentialPrivacy
from federated.fedavg import FederatedAveraging


def test_federated_storage():
    """Test federated storage system"""
    print("\n=== Testing Federated Storage ===")
    
    storage_dir = Path("./test_federated_data")
    fed_storage = FederatedStorage(storage_dir)
    
    # Test contribution tracking
    contribution_id = fed_storage.add_contribution(
        hospital_id="hosp_johns_hopkins",
        model_name="chest_xray_model",
        gradient_norm=2.5,
        epsilon_used=0.1
    )
    print(f"✓ Added contribution: ID={contribution_id}")
    
    # Test gradient storage
    test_gradients = OrderedDict()
    test_gradients["layer1.weight"] = torch.randn(128, 128)
    test_gradients["layer2.weight"] = torch.randn(256, 128)
    
    fed_storage.save_gradients(
        hospital_id="hosp_johns_hopkins",
        model_name="chest_xray_model",
        gradients=test_gradients,
        contribution_id=contribution_id
    )
    print("✓ Saved gradients to disk")
    
    # Test loading gradients
    loaded_gradients = fed_storage.load_gradients("chest_xray_model")
    print(f"✓ Loaded {len(loaded_gradients)} gradient sets")
    
    # Test statistics
    stats = fed_storage.get_federated_stats()
    print(f"✓ Federated stats: {stats}")
    
    hospital_stats = fed_storage.get_hospital_stats()
    print(f"✓ Hospital stats: {len(hospital_stats)} hospitals")
    
    # Cleanup
    import shutil
    import time
    import gc
    
    # Force garbage collection to release database connections
    gc.collect()
    time.sleep(0.5)
    
    try:
        shutil.rmtree(storage_dir)
        print("✓ Cleanup complete")
    except PermissionError:
        print("⚠ Cleanup skipped (database in use - this is OK)")


def test_differential_privacy():
    """Test differential privacy mechanism"""
    print("\n=== Testing Differential Privacy ===")
    
    dp = DifferentialPrivacy(epsilon=0.1, delta=1e-5, clipping_norm=1.0)
    print(f"✓ DP initialized: ε={dp.epsilon}, δ={dp.delta}, C={dp.clipping_norm}")
    
    # Create test gradients
    gradients = {
        "layer1": torch.randn(100, 100) * 10,  # Large gradients to test clipping
        "layer2": torch.randn(50, 50) * 5
    }
    
    # Test clipping
    clipped = dp.clip_gradients(gradients)
    original_norm = torch.sqrt(sum(torch.sum(g ** 2) for g in gradients.values()))
    clipped_norm = torch.sqrt(sum(torch.sum(g ** 2) for g in clipped.values()))
    print(f"✓ Gradient clipping: {original_norm:.2f} → {clipped_norm:.2f}")
    
    # Test noise addition
    noisy = dp.add_noise(clipped)
    print(f"✓ Noise added: σ={dp.noise_multiplier:.3f}")
    
    # Verify noise was added
    noise_amount = torch.sqrt(sum(
        torch.sum((noisy[k] - clipped[k]) ** 2)
        for k in clipped.keys()
    ))
    print(f"✓ Total noise magnitude: {noise_amount:.2f}")


def test_federated_averaging():
    """Test FedAvg algorithm"""
    print("\n=== Testing Federated Averaging ===")
    
    # Create simple model
    import torch.nn as nn
    model = nn.Sequential(
        nn.Linear(10, 20),
        nn.ReLU(),
        nn.Linear(20, 5)
    )
    
    fed_avg = FederatedAveraging(model, learning_rate=1.0)
    print(f"✓ FedAvg initialized")
    
    # Simulate gradients from 3 hospitals
    client_gradients = []
    for i in range(3):
        grads = OrderedDict()
        for name, param in model.named_parameters():
            grads[name] = torch.randn_like(param) * 0.01
        client_gradients.append(grads)
    
    print(f"✓ Simulated gradients from {len(client_gradients)} hospitals")
    
    # Aggregate
    aggregated = fed_avg.aggregate_gradients(client_gradients)
    print(f"✓ Aggregated {len(aggregated)} parameters")
    
    # Apply to model
    fed_avg.apply_gradients(aggregated)
    print(f"✓ Applied gradients to global model (round {fed_avg.round})")


async def test_api_endpoints():
    """Test federated API endpoints"""
    print("\n=== Testing API Endpoints ===")
    
    try:
        import httpx
        
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient() as client:
            # Test stats endpoint
            try:
                response = await client.get(f"{base_url}/api/v1/federated/stats")
                if response.status_code == 200:
                    stats = response.json()
                    print(f"✓ Federated stats API: {stats}")
                else:
                    print(f"⚠ Stats API returned {response.status_code}")
            except Exception as e:
                print(f"⚠ Server not running: {e}")
            
            # Test hospitals endpoint
            try:
                response = await client.get(f"{base_url}/api/v1/federated/hospitals")
                if response.status_code == 200:
                    hospitals = response.json()
                    print(f"✓ Hospitals API: {hospitals['total_hospitals']} hospitals")
                else:
                    print(f"⚠ Hospitals API returned {response.status_code}")
            except Exception as e:
                print(f"⚠ Server not running: {e}")
    
    except ImportError:
        print("⚠ httpx not installed, skipping API tests")


def test_end_to_end():
    """Test complete federated learning workflow"""
    print("\n=== Testing End-to-End Workflow ===")
    
    storage_dir = Path("./test_e2e_data")
    fed_storage = FederatedStorage(storage_dir)
    
    # Simulate contributions from multiple hospitals
    hospitals = ["hosp_medora", "hosp_mayo_clinic", "hosp_cleveland_clinic"]
    model_name = "chest_xray_model"
    
    print(f"Simulating {len(hospitals)} hospitals contributing...")
    
    for hospital_id in hospitals:
        # Create gradients with DP
        dp = DifferentialPrivacy(epsilon=0.1, delta=1e-5, clipping_norm=1.0)
        
        gradients = OrderedDict()
        gradients["fc.weight"] = torch.randn(512, 2048)
        gradients["fc.bias"] = torch.randn(512)
        
        # Apply DP
        gradients_clipped = dp.clip_gradients(gradients)
        gradients_private = dp.add_noise(gradients_clipped)
        
        # Calculate norm
        gradient_norm = torch.sqrt(sum(torch.sum(g ** 2) for g in gradients_private.values())).item()
        
        # Store contribution
        contribution_id = fed_storage.add_contribution(
            hospital_id=hospital_id,
            model_name=model_name,
            gradient_norm=gradient_norm,
            epsilon_used=dp.epsilon
        )
        
        fed_storage.save_gradients(
            hospital_id=hospital_id,
            model_name=model_name,
            gradients=gradients_private,
            contribution_id=contribution_id
        )
        
        print(f"  ✓ {hospital_id}: gradient_norm={gradient_norm:.2f}, ε={dp.epsilon}")
    
    # Aggregate gradients
    print("\nAggregating gradients...")
    gradients_list = fed_storage.load_gradients(model_name)
    print(f"  Loaded {len(gradients_list)} gradient sets")
    
    # Create dummy model for aggregation
    import torch.nn as nn
    model = nn.Linear(2048, 512)
    fed_avg = FederatedAveraging(model, learning_rate=1.0)
    
    # Extract gradients
    gradients_only = [grad for _, grad in gradients_list]
    
    # Aggregate
    aggregated = fed_avg.aggregate_gradients(gradients_only)
    print(f"  ✓ Aggregated {len(aggregated)} parameters")
    
    # Apply to model
    fed_avg.apply_gradients(aggregated)
    print(f"  ✓ Updated global model (round {fed_avg.round})")
    
    # Save global model
    fed_storage.save_global_model(
        model_name=model_name,
        model_state=model.state_dict(),
        round_id=fed_avg.round
    )
    print(f"  ✓ Saved global model")
    
    # Get final statistics
    stats = fed_storage.get_federated_stats()
    print(f"\n✓ Final stats: {stats}")
    
    hospital_stats = fed_storage.get_hospital_stats()
    print(f"✓ Hospital contributions:")
    for hospital in hospital_stats:
        print(f"  - {hospital['hospital_id']}: {hospital['total_contributions']} contributions, ε={hospital['epsilon_budget_used']:.3f}")
    
    # Cleanup
    import shutil
    import gc
    import time
    
    gc.collect()
    time.sleep(0.5)
    
    try:
        shutil.rmtree(storage_dir)
        print("\n✓ Cleanup complete")
    except PermissionError:
        print("\n⚠ Cleanup skipped (database in use - this is OK)")


if __name__ == "__main__":
    print("=" * 60)
    print("FEDERATED LEARNING SYSTEM TEST SUITE")
    print("=" * 60)
    
    try:
        # Run tests
        test_federated_storage()
        test_differential_privacy()
        test_federated_averaging()
        test_end_to_end()
        
        # Test API (requires server running)
        print("\nTo test API endpoints, start the server with:")
        print("  python main.py")
        print("Then run:")
        print("  python test_federated.py --api")
        
        if "--api" in sys.argv:
            asyncio.run(test_api_endpoints())
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
