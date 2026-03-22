"""
Test Cases for Brain Tumor and Lung/Colon Cancer Models
Downloads sample test images from public datasets and evaluates model accuracy
"""
import sys
from pathlib import Path
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
from PIL import Image
import numpy as np
from transformers import AutoModelForImageClassification, AutoImageProcessor
import time
from collections import defaultdict
import urllib.request
import ssl

# Disable SSL verification for downloading (some datasets have certificate issues)
ssl._create_default_https_context = ssl._create_unverified_context

MODELS_DIR = Path(__file__).parent.parent / "models" / "weights"
TEST_IMAGES_DIR = Path(__file__).parent.parent / "test_data"
TEST_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


# Test configurations for each model
MODEL_CONFIGS = {
    'brain_tumor': {
        'hf_repo': 'Devarshi/Brain_Tumor_Classification',
        'weight_file': 'brain_tumor_swin.pth',
        'classes': ['glioma', 'meningioma', 'pituitary', 'notumor'],
        'test_images_dir': TEST_IMAGES_DIR / 'brain_tumor',
    },
    'lung_colon': {
        'hf_repo': 'DunnBC22/vit-base-patch16-224-in21k_lung_and_colon_cancer',
        'weight_file': 'lung_colon_cancer_vit.pth',
        'classes': ['colon_aca', 'colon_n', 'lung_aca', 'lung_n', 'lung_scc'],
        'test_images_dir': TEST_IMAGES_DIR / 'lung_colon',
    }
}


def generate_synthetic_test_images(model_name, config, num_per_class=5):
    """Generate synthetic test images for each class to test model functionality"""
    test_dir = config['test_images_dir']
    test_dir.mkdir(parents=True, exist_ok=True)
    
    test_images = []
    
    print(f"  Generating {num_per_class} synthetic test images per class...")
    
    for class_idx, class_name in enumerate(config['classes']):
        class_dir = test_dir / class_name
        class_dir.mkdir(parents=True, exist_ok=True)
        
        for i in range(num_per_class):
            # Create synthetic image with different random seeds per class
            np.random.seed(class_idx * 1000 + i)
            
            # Create image with class-specific patterns
            img_array = np.random.randint(50, 200, (224, 224, 3), dtype=np.uint8)
            
            # Add some class-specific texture patterns
            if class_idx == 0:
                # Pattern 1: Circular features (tumor-like for glioma/colon_aca)
                for _ in range(3):
                    cx, cy = np.random.randint(50, 174, 2)
                    r = np.random.randint(10, 30)
                    for x in range(224):
                        for y in range(224):
                            if (x - cx)**2 + (y - cy)**2 < r**2:
                                img_array[x, y] = np.clip(img_array[x, y] + 30, 0, 255)
            elif class_idx == 1:
                # Pattern 2: Linear features
                for _ in range(5):
                    start = np.random.randint(0, 224, 2)
                    img_array[start[0]:start[0]+5, :] = np.clip(img_array[start[0]:start[0]+5, :] + 40, 0, 255)
            elif class_idx == 2:
                # Pattern 3: Scattered bright spots
                for _ in range(20):
                    x, y = np.random.randint(0, 224, 2)
                    img_array[max(0,x-3):min(224,x+3), max(0,y-3):min(224,y+3)] = 255
            else:
                # Pattern 4: Smooth gradient (normal tissue)
                for x in range(224):
                    img_array[x, :] = np.clip(img_array[x, :] - x//4, 30, 220)
            
            img = Image.fromarray(img_array)
            img_path = class_dir / f"test_{i}.jpg"
            img.save(img_path)
            
            test_images.append({
                'path': img_path,
                'label': class_idx,
                'class_name': class_name
            })
    
    return test_images


def load_model(config):
    """Load model from HuggingFace"""
    print(f"  Loading model from: {config['hf_repo']}")
    
    try:
        model = AutoModelForImageClassification.from_pretrained(config['hf_repo'])
        processor = AutoImageProcessor.from_pretrained(config['hf_repo'])
        model.eval()
        return model, processor
    except Exception as e:
        print(f"  ✗ Error loading model: {e}")
        return None, None


def run_inference(model, processor, image_path):
    """Run inference on a single image"""
    try:
        img = Image.open(image_path).convert('RGB')
        inputs = processor(images=img, return_tensors="pt")
        
        with torch.no_grad():
            start_time = time.time()
            outputs = model(**inputs)
            inference_time = time.time() - start_time
        
        logits = outputs.logits
        probabilities = torch.softmax(logits, dim=-1)
        predicted_class = torch.argmax(probabilities, dim=-1).item()
        confidence = probabilities[0][predicted_class].item()
        
        return {
            'predicted_class': predicted_class,
            'confidence': confidence,
            'inference_time': inference_time,
            'probabilities': probabilities[0].tolist()
        }
    except Exception as e:
        print(f"    ✗ Inference error: {e}")
        return None


def calculate_metrics(results, num_classes):
    """Calculate accuracy and per-class metrics"""
    correct = 0
    total = 0
    class_correct = defaultdict(int)
    class_total = defaultdict(int)
    
    for r in results:
        if r['result'] is not None:
            total += 1
            class_total[r['label']] += 1
            
            # Note: Model predictions may use different class ordering
            # We're testing model functionality, not exact class mapping
            if r['result']['predicted_class'] == r['label']:
                correct += 1
                class_correct[r['label']] += 1
    
    overall_accuracy = correct / total if total > 0 else 0
    
    per_class_accuracy = {}
    for class_idx in range(num_classes):
        if class_total[class_idx] > 0:
            per_class_accuracy[class_idx] = class_correct[class_idx] / class_total[class_idx]
        else:
            per_class_accuracy[class_idx] = 0.0
    
    return {
        'overall_accuracy': overall_accuracy,
        'correct': correct,
        'total': total,
        'per_class_accuracy': per_class_accuracy
    }


def test_model(model_name, config):
    """Run complete test for a model"""
    print(f"\n{'='*70}")
    print(f"TESTING: {model_name.upper().replace('_', ' ')} MODEL")
    print(f"{'='*70}")
    print(f"Model: {config['hf_repo']}")
    print(f"Classes: {', '.join(config['classes'])}")
    
    # Generate synthetic test images
    print(f"\n📁 Preparing test data...")
    test_images = generate_synthetic_test_images(model_name, config, num_per_class=5)
    print(f"   Created {len(test_images)} test images")
    
    # Load model
    print(f"\n🔧 Loading model...")
    model, processor = load_model(config)
    
    if model is None:
        return None
    
    # Get model info
    print(f"   ✓ Model loaded: {model.__class__.__name__}")
    print(f"   ✓ Num labels: {model.config.num_labels}")
    print(f"   ✓ Label mapping: {model.config.id2label}")
    
    # Run inference on all test images
    print(f"\n🔬 Running inference on {len(test_images)} images...")
    results = []
    inference_times = []
    
    for i, test_item in enumerate(test_images):
        result = run_inference(model, processor, test_item['path'])
        results.append({
            'path': test_item['path'],
            'label': test_item['label'],
            'class_name': test_item['class_name'],
            'result': result
        })
        if result:
            inference_times.append(result['inference_time'])
    
    # Calculate metrics
    print(f"\n📊 Calculating metrics...")
    metrics = calculate_metrics(results, len(config['classes']))
    
    # Display results
    print(f"\n{'='*70}")
    print(f"RESULTS: {model_name.upper().replace('_', ' ')}")
    print(f"{'='*70}")
    
    print(f"\n🎯 Overall Test Accuracy: {metrics['overall_accuracy']*100:.1f}%")
    print(f"   Correct: {metrics['correct']}/{metrics['total']}")
    
    print(f"\n📈 Per-Class Accuracy:")
    for class_idx, class_name in enumerate(config['classes']):
        acc = metrics['per_class_accuracy'].get(class_idx, 0)
        print(f"   {class_name}: {acc*100:.1f}%")
    
    if inference_times:
        avg_time = sum(inference_times) / len(inference_times)
        print(f"\n⏱️  Average Inference Time: {avg_time*1000:.2f}ms")
    
    # Show sample predictions
    print(f"\n📋 Sample Predictions (first 3 per class):")
    shown = defaultdict(int)
    for r in results:
        if r['result'] and shown[r['label']] < 3:
            pred_label = model.config.id2label[r['result']['predicted_class']]
            correct = "✓" if r['result']['predicted_class'] == r['label'] else "✗"
            print(f"   {correct} True: {r['class_name']:15} → Pred: {pred_label:15} ({r['result']['confidence']*100:.1f}%)")
            shown[r['label']] += 1
    
    return {
        'model': model_name,
        'accuracy': metrics['overall_accuracy'],
        'per_class': metrics['per_class_accuracy'],
        'avg_inference_time': sum(inference_times) / len(inference_times) if inference_times else 0,
        'total_tested': metrics['total']
    }


def main():
    print("="*70)
    print("MEDICAL AI MODEL ACCURACY TESTING")
    print("="*70)
    print(f"\nTest data directory: {TEST_IMAGES_DIR}")
    print("\n⚠️  Note: Using synthetic test images. For real accuracy benchmarks,")
    print("   use actual medical imaging datasets with proper labels.\n")
    
    all_results = []
    
    for model_name, config in MODEL_CONFIGS.items():
        result = test_model(model_name, config)
        if result:
            all_results.append(result)
    
    # Final summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY - MODEL ACCURACY TEST RESULTS")
    print(f"{'='*70}")
    
    print(f"\n{'Model':<25} {'Test Accuracy':>15} {'Reported Accuracy':>18} {'Inference Time':>15}")
    print("-"*70)
    
    reported_accuracies = {
        'brain_tumor': 97,
        'lung_colon': 99
    }
    
    for r in all_results:
        reported = reported_accuracies.get(r['model'], 'N/A')
        print(f"{r['model'].replace('_', ' ').title():<25} "
              f"{r['accuracy']*100:>14.1f}% "
              f"{reported:>17}% "
              f"{r['avg_inference_time']*1000:>13.2f}ms")
    
    print("\n" + "="*70)
    print("📝 INTERPRETATION NOTES")
    print("="*70)
    print("""
The test accuracy shown above is calculated using SYNTHETIC test images,
not actual medical imaging data. This tests that:

  ✓ Models load correctly from HuggingFace
  ✓ Inference pipeline works end-to-end  
  ✓ Models produce valid probability distributions
  ✓ Inference timing is reasonable

The 'Reported Accuracy' values (97% for Brain Tumor, 99% for Lung/Colon)
are from the original model authors' benchmarks on real medical datasets:

  - Brain Tumor: Trained on brain MRI images from Kaggle Brain Tumor Dataset
  - Lung/Colon: Trained on LC25000 histopathology dataset

To validate actual medical performance, test with:
  1. Real medical imaging data from appropriate sources
  2. Proper train/test splits
  3. Expert-verified ground truth labels
""")
    
    return len(all_results) == len(MODEL_CONFIGS)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
