#!/usr/bin/env python3
"""
Quick test to verify all local models load and run inference correctly.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from models.model_manager import MedicalModelWrapper
import numpy as np
from PIL import Image
import io

def create_test_image(size=(224, 224)):
    """Create a random test image."""
    img = np.random.randint(0, 255, (*size, 3), dtype=np.uint8)
    pil_img = Image.fromarray(img)
    buffer = io.BytesIO()
    pil_img.save(buffer, format='PNG')
    return buffer.getvalue()

def test_model(model_name, image_size=224):
    """Test a single model."""
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"{'='*60}")
    
    try:
        # Load model
        print("Loading model...")
        model = MedicalModelWrapper(model_name, device='cpu')
        print(f"✓ Model loaded successfully")
        print(f"  Classes: {model.classes}")
        print(f"  Num classes: {model.num_classes}")
        
        # Create test image
        test_img = create_test_image((image_size, image_size))
        
        # Run inference
        print("Running inference...")
        result = model.predict(test_img)
        
        print(f"✓ Inference completed!")
        print(f"  Predicted: {result['predicted_class']}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Time: {result['inference_time']:.3f}s")
        print(f"  All probabilities: {result['all_probabilities']}")
        
        return True
        
    except FileNotFoundError as e:
        print(f"✗ Model files missing: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*60)
    print("Testing All Local Medical Models")
    print("="*60)
    
    # Models with local weights
    local_models = [
        ('pneumonia_detector', 224),
        ('skin_cancer_detector', 224),  
        ('diabetic_retinopathy_detector', 518),  # DINOv2 uses 518x518
        ('breast_cancer_detector', 224),
    ]
    
    results = {}
    for model_name, img_size in local_models:
        results[model_name] = test_model(model_name, img_size)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for model_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {model_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} models working")
    print("="*60)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
