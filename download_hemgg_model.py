
from huggingface_hub import snapshot_download
from pathlib import Path
import os

target_dir = Path("/var/www/medora/models/weights/bone_fracture_hemgg")
target_dir.mkdir(parents=True, exist_ok=True)

print(f"Downloading Hemgg/bone-fracture-detection-using-xray to {target_dir}...")

try:
    snapshot_download(
        repo_id="Hemgg/bone-fracture-detection-using-xray",
        local_dir=str(target_dir),
        local_dir_use_symlinks=False,
        ignore_patterns=["*.msgpack", "*.h5", "*.tflite"]
    )
    print("Download complete.")
except Exception as e:
    print(f"Download failed: {e}")
