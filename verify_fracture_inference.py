
import logging
import torch
import numpy as np
from PIL import Image
from transformers import AutoModelForImageClassification, AutoImageProcessor
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODELS_DIR = "/var/www/medora/models/weights/bone_fracture_hemgg"
DEVICE = "cpu"

def test_inference():
    logger.info("Loading model...")
    processor = AutoImageProcessor.from_pretrained(MODELS_DIR, local_files_only=True)
    model = AutoModelForImageClassification.from_pretrained(MODELS_DIR, local_files_only=True)
    model.eval()
    
    logger.info(f"Model Labels: {model.config.id2label}")
    
    # Create dummy images
    logger.info("Creating dummy images...")
    
    # 1. Random noise (simulating structure)
    noise_img = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
    
    # 2. Black image
    black_img = Image.new('RGB', (224, 224), color='black')
    
    # 3. White image
    white_img = Image.new('RGB', (224, 224), color='white')
    
    # 4. Inverted Noise (White background-ish)
    inv_noise = Image.eval(noise_img, lambda x: 255 - x)
    
    # 5. User Uploaded X-Ray
    user_xray_path = Path.home() / "debug_xray.png"
    user_xray = Image.open(user_xray_path).convert("RGB")

    # 6. Inverted User X-Ray
    inv_user_xray = Image.eval(user_xray, lambda x: 255 - x)

    tests = [
        ("Random Noise", noise_img), 
        ("Black Image", black_img), 
        ("White Image", white_img),
        ("Inverted Noise", inv_noise),
        ("User X-Ray", user_xray),
        ("Inverted User X-Ray", inv_user_xray)
    ]
    
    for name, img in tests:
        logger.info(f"\nTesting {name}:")
        inputs = processor(images=img, return_tensors="pt")
        
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits[0], dim=0)
            
        logger.info(f"Logits: {logits}")
        logger.info(f"Probs: {probs}")
        logger.info(f"Class 0 (Fractured): {probs[0]:.4f}")
        logger.info(f"Class 1 (Not Fractured): {probs[1]:.4f}")
        
if __name__ == "__main__":
    test_inference()
