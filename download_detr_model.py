
from huggingface_hub import snapshot_download
from pathlib import Path
import os

target_dir = Path("/var/www/medora/models/weights/bone_fracture_detr")
target_dir.mkdir(parents=True, exist_ok=True)

print(f"Downloading Judy07/bone-fracture-DETA to {target_dir}...")

try:
    snapshot_download(
        repo_id="Judy07/bone-fracture-DETA",
        local_dir=str(target_dir),
        local_dir_use_symlinks=False,
        ignore_patterns=["*.msgpack", "*.h5", "*.tflite"]
    )
    print("Download complete.")
except Exception as e:
    print(f"Download failed: {e}")
