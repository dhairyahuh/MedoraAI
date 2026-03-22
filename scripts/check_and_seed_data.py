"""
Check and seed federated learning data
"""
from federated.federated_storage import FederatedStorage
from pathlib import Path
import config
import torch
from collections import OrderedDict
import random

storage_dir = Path(config.BASE_DIR) / "federated_data"
fs = FederatedStorage(storage_dir)

# Check current stats
stats = fs.get_federated_stats()
print("\n=== Current Database Stats ===")
print(f"Contributions: {stats['total_contributions']}")
print(f"Active Hospitals: {stats['active_hospitals']}")
print(f"Training Rounds: {stats['total_rounds']}")
print(f"Model Accuracy: {stats['latest_accuracy']}")
print(f"Average Epsilon: {stats['average_epsilon']}")

# If empty, seed some data
if stats['total_contributions'] == 0:
    print("\n=== Seeding Initial Data ===")
    
    # Simulate 5 hospitals with contributions
    hospitals = ["Medora", "Mayo Clinic", "Cleveland Clinic", "Mass General", "Stanford Health"]
    models = ["chest_xray_model", "skin_lesion_model", "brain_mri_model"]
    
    for i, hospital in enumerate(hospitals):
        for model in models:
            # Create fake gradients
            gradients = OrderedDict()
            for j in range(159):  # Match real model parameter count
                gradients[f"layer_{j}.weight"] = torch.randn(128, 64) * 0.01
            
            # Add contribution
            contribution_id = fs.add_contribution(
                hospital_id=hospital,
                model_name=model,
                gradient_norm=random.uniform(0.5, 2.0),
                epsilon_used=0.1
            )
            
            # Save gradients
            fs.save_gradients(
                hospital_id=hospital,
                model_name=model,
                gradients=gradients,
                contribution_id=contribution_id
            )
            
            # Increment inference count
            for _ in range(random.randint(5, 20)):
                fs.increment_inference_count(hospital)
    
    # Add model accuracy metrics directly
    for model in models:
        for round_num in range(1, 4):
            accuracy = 0.85 + random.uniform(0, 0.1)
            fs.update_model_accuracy(model, accuracy)
    
    print("✓ Seeded data for 5 hospitals")
    print("✓ Added model accuracy metrics")

# Check updated stats
stats = fs.get_federated_stats()
print("\n=== Updated Database Stats ===")
print(f"Contributions: {stats['total_contributions']}")
print(f"Active Hospitals: {stats['active_hospitals']}")
print(f"Training Rounds: {stats['total_rounds']}")
print(f"Model Accuracy: {stats['latest_accuracy'] * 100:.1f}%")
print(f"Average Epsilon: {stats['average_epsilon']}")

# Show hospital stats
hospitals = fs.get_hospital_stats()
print(f"\n=== Hospital Details ===")
for h in hospitals:
    print(f"{h['hospital_id']}: {h['total_contributions']} contributions, {h['total_inferences']} inferences")
