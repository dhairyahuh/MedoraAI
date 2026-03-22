
import os
import time
import torch
import logging
from pathlib import Path
from transformers import AutoModelForImageClassification, AutoImageProcessor, AutoConfig

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path("/var/www/medora")
MODELS_DIR_PATH = BASE_DIR / "models" / "weights" / "bone_fracture"
DEVICE = "cpu"  # Force CPU for testing worst case

def test_load_fracture_detector():
    logger.info("Starting Fracture Detector load test...")
    logger.info(f"Checking directory: {MODELS_DIR_PATH}")
    
    if not MODELS_DIR_PATH.exists():
        logger.error(f"Directory not found!")
        return
        
    start_time = time.time()
    
    try:
        logger.info("Loading Config...")
        model_config = AutoConfig.from_pretrained(
            str(MODELS_DIR_PATH),
            local_files_only=True
        )
        logger.info(f"Config loaded. Time: {time.time() - start_time:.2f}s")
        
        logger.info("Instantiating Model Structure...")
        model = AutoModelForImageClassification.from_config(model_config)
        logger.info(f"Structure instantiated. Time: {time.time() - start_time:.2f}s")
        
        weights_path = MODELS_DIR_PATH / "model.safetensors"
        logger.info(f"Loading Weights from {weights_path}...")
        
        # Explicitly time the torch.load
        t0 = time.time()
        from safetensors.torch import load_file
        state_dict = load_file(str(weights_path), device=DEVICE)
        logger.info(f"Weights loaded into RAM. Load Time: {time.time() - t0:.2f}s")
        
        t1 = time.time()
        model.load_state_dict(state_dict, strict=True)
        logger.info(f"State dict applied to model. Apply Time: {time.time() - t1:.2f}s")
        
        model.to(DEVICE)
        model.eval()
        
        total_time = time.time() - start_time
        logger.info(f"✓ SUCCESS! Total Load Time: {total_time:.2f}s")
        
    except Exception as e:
        logger.error(f"FAILED: {e}", exc_info=True)

if __name__ == "__main__":
    test_load_fracture_detector()
