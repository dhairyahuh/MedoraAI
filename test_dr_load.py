
import logging
import torch
from transformers import AutoModelForImageClassification, AutoImageProcessor
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_load_diabetic_retinopathy():
    model_dir = Path("/var/www/medora/models/weights/diabetic_retinopathy")
    
    print(f"Testing loading from: {model_dir}")
    if not model_dir.exists():
        print(f"ERROR: Directory mismatch. Path {model_dir} does not exist")
        return

    try:
        print("Loading Image Processor...")
        processor = AutoImageProcessor.from_pretrained(
            str(model_dir),
            local_files_only=True,
            trust_remote_code=False
        )
        print("✓ Image Processor loaded")
        
        print("Loading Model...")
        model = AutoModelForImageClassification.from_pretrained(
            str(model_dir),
            local_files_only=True,
            trust_remote_code=False
        )
        print("✓ Model loaded")
        
        # Test inference with dummy input
        print("Testing dummy inference...")
        dummy_input = torch.randn(1, 3, 518, 518)  # DINOv2 uses 518x518
        with torch.no_grad():
            outputs = model(dummy_input)
            print("✓ Inference successful")
            print(f"Output shape: {outputs.logits.shape}")

    except Exception as e:
        print(f"❌ FAILED with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_load_diabetic_retinopathy()
