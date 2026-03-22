
import sys
import os
import logging
from pathlib import Path

# Add project root to path
sys.path.append("/var/www/medora")

import config
from models import model_manager

# Configure logging
logging.basicConfig(level=logging.INFO)

# Mock request data
img_path = Path.home() / "debug_xray.png"
with open(img_path, "rb") as f:
    image_bytes = f.read()

request_data = {
    "model": "fracture_detector",
    "image": image_bytes
}

print("Running inference test through model_manager...")
try:
    result = model_manager.run_inference_worker(request_data)
    print("Inference Result:", result)
except Exception as e:
    print("Inference Failed:", e)
    import traceback
    traceback.print_exc()
