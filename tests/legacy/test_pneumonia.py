#!/usr/bin/env python3
"""
Quick test for Pneumonia model integration
Tests that the offline Pneumonia model loads and runs inference correctly.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from models.model_manager import MedicalModelWrapper

def main():
    print("="*60)
    print("Testing Pneumonia Model (Offline)")
    print("="*60)
    
    try:
        # Load model
        print("\n1. Loading model...")
        model = MedicalModelWrapper('pneumonia_detector', device='cpu')
        print("   ✓ Model loaded successfully")
        
        # Check weights
        weights_path = Path("models/weights/pneumonia_vit.pth")
        if weights_path.exists():
            size_mb = weights_path.stat().st_size / (1024 * 1024)
            print(f"   ✓ Weights file found ({size_mb:.1f} MB)")
        else:
            print("   ✗ Weights file missing!")
            print(f"   Expected at: {weights_path.absolute()}")
            return False
        
        # Test with real images from test_images directory
        print("\n2. Testing inference with real chest X-ray images...")
        
        # Path to test images directory
        test_images_dir = Path("model_pneumonia/medical-model-inference-test/test_images")
        
        if not test_images_dir.exists():
            print(f"   ✗ Test images directory not found: {test_images_dir.absolute()}")
            return False
        
        # Find all image files in the directory
        image_extensions = {'.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG'}
        image_files = [
            f for f in test_images_dir.iterdir() 
            if f.suffix in image_extensions and f.is_file()
        ]
        
        if not image_files:
            print(f"   ✗ No image files found in {test_images_dir.absolute()}")
            return False
        
        # Sort for consistent ordering
        image_files.sort()
        
        print(f"   ✓ Found {len(image_files)} test image(s)")
        
        # Test with the first image (or all images)
        test_count = min(3, len(image_files))  # Test up to 3 images
        results = []
        
        for i, image_path in enumerate(image_files[:test_count], 1):
            print(f"\n   Testing image {i}/{test_count}: {image_path.name}")
            
            # Load image file
            try:
                with open(image_path, 'rb') as f:
                    image_bytes = f.read()
            except Exception as e:
                print(f"   ✗ Failed to read image: {e}")
                continue
            
            # Run inference
            result = model.predict(image_bytes)
            results.append(result)
            
            print(f"     ✓ Prediction: {result['predicted_class']}")
            print(f"     ✓ Confidence: {result['confidence']:.2%}")
            print(f"     ✓ Inference Time: {result['inference_time']:.3f}s")
            print(f"     Probabilities:")
            for class_name, prob in result['all_probabilities'].items():
                print(f"       - {class_name}: {prob:.2%}")
        
        if not results:
            print("   ✗ No successful inferences")
            return False
        
        # Verify model is using transformers (offline)
        if hasattr(model.model, 'config'):
            print(f"\n   ✓ Using transformers ViT model (offline)")
            print(f"   ✓ Model config: {model.model.config.model_type}")
        
        # Summary
        avg_confidence = sum(r['confidence'] for r in results) / len(results)
        print(f"\n   Summary:")
        print(f"     - Images tested: {len(results)}")
        print(f"     - Average confidence: {avg_confidence:.2%}")
        
        print("\n" + "="*60)
        print("✓ All tests passed! Pneumonia model is working.")
        print("="*60)
        return True
        
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("   Make sure weights file is at: models/weights/pneumonia_vit.pth")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
