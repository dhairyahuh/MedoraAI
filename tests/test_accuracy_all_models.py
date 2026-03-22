import sys
import os
import torch
import time
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageDraw
import numpy as np

# Setup path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from models.model_manager import MedicalModelWrapper

# Config for test generation
TEST_CONFIG = {
    'pneumonia_detector': {'classes': ['Normal', 'Pneumonia']},
    'skin_cancer_detector': {'classes': ['Actinic-keratoses', 'Basal-cell-carcinoma', 'Benign-keratosis-like-lesions', 'Dermatofibroma', 'Melanocytic-nevi', 'Melanoma', 'Vascular-lesions']},
    'tumor_detector': {'classes': ['glioma_tumor', 'meningioma_tumor', 'no_tumor', 'pituitary_tumor']},
    'lung_nodule_detector': {'classes': ['Adenocarcinoma', 'Large Cell Carcinoma', 'Normal', 'Squamous Cell Carcinoma']},
    'breast_cancer_detector': {'classes': ['Benign', 'Malignant']},
    'diabetic_retinopathy_detector': {'classes': ['No DR', 'Mild', 'Moderate', 'Severe', 'Proliferative DR']},
    # New models
    'polyp_detector': {'classes': ['CT_COVID', 'CT_NonCOVID']},
    'cancer_grading_detector': {'classes': ['negative', 'positive']},
    'fracture_detector': {'classes': ['Fractured', 'Not Fractured']},
    'ultrasound_classifier': {'classes': ['benign', 'malignant', 'normal']}
}

def generate_synthetic_image(model_name, class_idx, size=224):
    """Generate a synthetic image with some simple class-distinctive patterns (heuristics)"""
    # Create base image
    img_array = np.random.randint(50, 200, (size, size, 3), dtype=np.uint8)
    img = Image.fromarray(img_array)
    draw = ImageDraw.Draw(img)
    
    # Add patterns based on index to try and distinguish (very rudimentary)
    # This won't fool a real deep learning model trained on real textures, 
    # but ensures inputs are different per class.
    
    if class_idx % 2 == 0:
        # Circles for even classes
        draw.ellipse([50, 50, 150, 150], fill=(200, 100, 100))
    else:
        # Rectangles for odd classes
        draw.rectangle([50, 50, 150, 150], fill=(100, 200, 100))
        
    # Model specific simple patterns
    if 'fracture' in model_name and class_idx == 0: # Fractured
        draw.line([0, 0, size, size], fill=(255, 255, 255), width=5)
        
    if 'pneumonia' in model_name and class_idx == 1: # Pneumonia (cloudy)
        # Add random noise patch
        noise = np.random.randint(100, 255, (100, 100, 3), dtype=np.uint8)
        img.paste(Image.fromarray(noise), (60, 60))

    buf = BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()

def evaluate_model(model_name):
    print(f"\nEvaluating {model_name}...")
    try:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        wrapper = MedicalModelWrapper(model_name, device=device)
        classes = TEST_CONFIG[model_name]['classes']
        
        # Determine image size 
        spec = config.MODEL_SPECS.get(model_name, {})
        img_size = spec.get('image_size', 224)
        
        correct = 0
        total = 0
        times = []
        
        # Test 5 images per class
        for true_idx, true_class in enumerate(classes):
            for i in range(5):
                img_bytes = generate_synthetic_image(model_name, true_idx, img_size)
                
                start = time.time()
                result = wrapper.predict(img_bytes)
                times.append(time.time() - start)
                
                # Check prediction
                pred_class = result.get('predicted_class')
                
                if pred_class == true_class:
                    correct += 1
                total += 1
                
                # Print first sample of each class
                if i == 0:
                     print(f"  Class '{true_class}': Predicted '{pred_class}' (Conf: {result.get('confidence', 0):.2f})")

        accuracy = correct / total
        avg_time = sum(times) / len(times)
        
        print(f"  ➜ Accuracy (on synthetic): {accuracy*100:.1f}% ({correct}/{total})")
        print(f"  ➜ Avg Inference Time: {avg_time*1000:.1f}ms")
        
        return {
            'model': model_name,
            'accuracy': accuracy,
            'avg_time': avg_time,
            'status': 'PASS'
        }

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return {'model': model_name, 'status': 'FAIL', 'error': str(e)}

def main():
    print("="*70)
    print("MEDICAL AI MODEL ACCURACY BENCHMARK (SYNTHETIC DATA)")
    print("="*70)
    print("Note: Accuracies will be low/random because tests use synthetic patterns,")
    print("not real medical images. This verifies the evaluation pipeline functions.\n")
    
    results = []
    for model in TEST_CONFIG.keys():
        results.append(evaluate_model(model))
        
    print("\n" + "="*70)
    print("FINAL RESULTS SUMMARY")
    print("="*70)
    print(f"{'Model':<30} {'Status':<10} {'Time (ms)':<10} {'Accuracy':<10}")
    print("-" * 70)
    
    failures = 0
    for r in results:
        if r['status'] == 'PASS':
            print(f"{r['model']:<30} {r['status']:<10} {r['avg_time']*1000:<10.1f} {r['accuracy']*100:.1f}%")
        else:
            print(f"{r['model']:<30} {r['status']:<10} {'-':<10} -")
            failures += 1
            
    return failures == 0

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
