from federated.federated_storage import FederatedStorage
from pathlib import Path
import config

storage_dir = Path(config.BASE_DIR) / "federated_data"
fs = FederatedStorage(storage_dir)
stats = fs.get_federated_stats()
print(f"Model Accuracy: {stats['latest_accuracy'] * 100:.1f}%")
print(f"Contributions: {stats['total_contributions']}")
print(f"Active Hospitals: {stats['active_hospitals']}")
