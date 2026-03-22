import sys
import os
import torch
from pathlib import Path
from PIL import Image

# Setup path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from models.model_manager import MedicalModelWrapper

def test_local_images():
    print("="*60)
    print("FRACTURE DETECTOR LOCAL TEST TOOL")
    print("="*60)
    
    # Define test directory
    test_dir = Path("test_data/fracture_test")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Load model
    print("Loading fracture_detector...")
    try:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        wrapper = MedicalModelWrapper('fracture_detector', device=device)
        print(f"✓ Model loaded successfully")
        print(f"✓ Label Mapping (Internal): {wrapper.classes}\n")
        # wrapper.classes should be ['Fractured', 'Not Fractured']
        # Index 0 -> Fractured
        # Index 1 -> Not Fractured
        
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        return

    # Check for images
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']
    images = [f for f in test_dir.iterdir() if f.suffix.lower() in image_extensions]
    
    if not images:
        print(f"⚠️  No images found in {test_dir.absolute()}")
        print("   Please place your X-ray images in this folder and run the script again.")
        print("   Example: test_data/fracture_test/my_xray.jpg")
        return

    print(f"Found {len(images)} images. Running inference...\n")
    
    for img_path in images:
        print(f"Analyzing {img_path.name}...")
        try:
            # Read image bytes
            with open(img_path, "rb") as f:
                img_bytes = f.read()
            
            # Predict
            result = wrapper.predict(img_bytes)
            
            # Display result
            pred_class = result['predicted_class']
            conf = result['confidence']
            
            print(f"  ➜ Prediction: {pred_class.upper()}")
            print(f"  ➜ Confidence: {conf*100:.1f}%")
            print(f"  ➜ Raw Probs: {result.get('all_probabilities', 'N/A')}")
            
            # Check for potential false negative/positive warning based on confidence
            if 0.4 < conf < 0.6:
                print("  ⚠️  Low confidence - results may be uncertain.")
            
            if pred_class == 'Not Fractured' and conf > 0.8:
                print("  ℹ️  Model is strongly confident this is NORMAL.")
                
        except Exception as e:
            print(f"  ✗ Error processing image: {e}")
        print("-" * 40)

if __name__ == "__main__":
    test_local_images()
