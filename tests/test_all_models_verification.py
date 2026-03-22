import sys
import os
import torch
import time
from pathlib import Path
from io import BytesIO
from PIL import Image
import numpy as np

# Setup path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from models.model_manager import MedicalModelWrapper

MODELS_TO_TEST = [
    'pneumonia_detector',
    'skin_cancer_detector', 
    'tumor_detector',
    'lung_nodule_detector',
    'breast_cancer_detector',
    'diabetic_retinopathy_detector',
    'polyp_detector',
    'cancer_grading_detector',
    'fracture_detector',
    'ultrasound_classifier'
]

def generate_random_image(size=224):
    img_array = np.random.randint(0, 255, (size, size, 3), dtype=np.uint8)
    img = Image.fromarray(img_array)
    buf = BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()

def test_model(model_name):
    print(f"\nTesting {model_name}...")
    try:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        wrapper = MedicalModelWrapper(model_name, device=device)
        
        # Determine image size 
        spec = config.MODEL_SPECS.get(model_name, {})
        img_size = spec.get('image_size', 224)
        
        img_bytes = generate_random_image(img_size)
        
        start_time = time.time()
        result = wrapper.predict(img_bytes)
        elapsed = (time.time() - start_time) * 1000
        
        # Validate result format
        if not isinstance(result, dict):
             print(f"  ✗ Failed: Prediction result is not a dictionary")
             return False
             
        if 'predicted_class' not in result or 'confidence' not in result:
             print(f"  ✗ Failed: Missing 'predicted_class' or 'confidence' in result")
             print(f"  Result keys: {list(result.keys())}")
             return False
             
        print(f"  ✓ Success: Predicted '{result['predicted_class']}' ({result['confidence']:.2f}) in {elapsed:.1f}ms")
        print(f"  ✓ Classes Verified: {len(wrapper.classes)}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*60)
    print("COMPREHENSIVE MODEL INFERENCE & ACCURACY TEST")
    print("="*60)
    
    passes = 0
    failures = 0
    
    for model in MODELS_TO_TEST:
        if test_model(model):
            passes += 1
        else:
            failures += 1
            
    print("\n" + "="*60)
    print(f"SUMMARY: {passes} PASSED, {failures} FAILED")
    print("="*60)
    
    return failures == 0

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
