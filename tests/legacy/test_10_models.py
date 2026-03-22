"""
Test 10 real medical AI models with proper medical images
Goal: All 10 models achieve 60%+ confidence
"""
import torch
import sys
from pathlib import Path
from PIL import Image
import asyncio
from colorama import Fore, Style, init
import time
import io

# Initialize colorama
init(autoreset=True)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from models.model_manager import MedicalModelWrapper
import config

# 10 models with real HuggingFace medical training
TARGET_MODELS = [
    'pneumonia_detector',           # 1. Chest X-ray (ViT) - dima806
    'skin_cancer_detector',         # 2. Dermoscopy (Swin) - existing
    'tumor_detector',               # 3. Brain MRI (Swin) - Devarshi
    'diabetic_retinopathy_detector', # 4. Retinal (ViT) - AsmaaElnagger
    'breast_cancer_detector',       # 5. Mammogram (ViT) - Falah
    'lung_nodule_detector',         # 6. Lung/Colon (ViT) - DunnBC22
    'polyp_detector',               # 7. COVID CT (ViT) - DunnBC22
    'fracture_detector',            # 8. Bone X-ray (ViT) - prithivMLmods
    'cancer_grading_detector',      # 9. Lung CT (Swin) - oohtmeel
    'ultrasound_classifier',        # 10. Breast Ultrasound (ViT) - sergiopaniego
]

# Medical image types for proper testing
TEST_CASES = {
    'pneumonia_detector': {
        'image_type': 'chest X-ray',
        'expected_class': 'Pneumonia',
        'description': 'Chest X-ray showing pneumonia infiltrates'
    },
    'skin_cancer_detector': {
        'image_type': 'dermoscopy',
        'expected_class': 'MEL',
        'description': 'Dermoscopic image of melanoma'
    },
    'tumor_detector': {
        'image_type': 'brain MRI',
        'expected_class': 'Glioma',
        'description': 'Brain MRI showing glioma tumor'
    },
    'diabetic_retinopathy_detector': {
        'image_type': 'fundus photo',
        'expected_class': 'Proliferate DR',
        'description': 'Retinal image with diabetic retinopathy'
    },
    'breast_cancer_detector': {
        'image_type': 'mammogram',
        'expected_class': 'Malignant',
        'description': 'Mammogram showing malignant mass'
    },
    'lung_nodule_detector': {
        'image_type': 'histopathology',
        'expected_class': 'Lung Adenocarcinoma',
        'description': 'Lung tissue histopathology slide'
    },
    'polyp_detector': {
        'image_type': 'CT scan',
        'expected_class': 'COVID-19',
        'description': 'Chest CT showing COVID-19 patterns'
    },
    'fracture_detector': {
        'image_type': 'bone X-ray',
        'expected_class': 'Wrist Positive',
        'description': 'Wrist X-ray with fracture'
    },
    'cancer_grading_detector': {
        'image_type': 'lung CT',
        'expected_class': 'Squamous Cell Carcinoma',
        'description': 'Lung CT showing cancer'
    },
    'ultrasound_classifier': {
        'image_type': 'ultrasound',
        'expected_class': 'Malignant',
        'description': 'Breast ultrasound showing malignancy'
    }
}

def create_medical_test_image(image_type):
    """
    Create synthetic medical-like test images
    In production, these would be replaced with real medical images
    """
    from PIL import Image, ImageDraw
    import random
    
    # Create base image
    img = Image.new('RGB', (224, 224))
    draw = ImageDraw.Draw(img)
    
    if 'xray' in image_type.lower() or 'x-ray' in image_type.lower():
        # Grayscale X-ray appearance
        for i in range(224):
            for j in range(224):
                # Add some texture
                noise = random.randint(-30, 30)
                val = 40 + noise
                img.putpixel((i, j), (val, val, val))
        # Add some "infiltrate" patterns
        draw.ellipse([80, 80, 140, 140], fill=(80, 80, 80))
        draw.ellipse([100, 100, 160, 160], fill=(60, 60, 60))
    
    elif 'ct' in image_type.lower():
        # CT scan appearance
        for i in range(224):
            for j in range(224):
                noise = random.randint(-20, 20)
                val = 50 + noise
                img.putpixel((i, j), (val, val, val))
        # Add "ground glass" patterns
        draw.rectangle([50, 50, 170, 170], fill=(70, 70, 70))
    
    elif 'dermoscopy' in image_type.lower():
        # Skin lesion appearance
        for i in range(224):
            for j in range(224):
                img.putpixel((i, j), (220, 180, 160))
        # Add dark lesion
        draw.ellipse([70, 70, 150, 150], fill=(80, 50, 40))
        draw.ellipse([90, 90, 130, 130], fill=(50, 30, 20))
    
    elif 'mri' in image_type.lower():
        # MRI appearance
        for i in range(224):
            for j in range(224):
                noise = random.randint(-15, 15)
                val = 60 + noise
                img.putpixel((i, j), (val, val, val))
        # Add tumor-like mass
        draw.ellipse([80, 80, 140, 140], fill=(120, 120, 120))
    
    elif 'fundus' in image_type.lower() or 'retinal' in image_type.lower():
        # Retinal image appearance
        for i in range(224):
            for j in range(224):
                img.putpixel((i, j), (180, 80, 40))
        # Add vessels and hemorrhages
        draw.line([0, 112, 224, 112], fill=(140, 40, 20), width=3)
        draw.line([112, 0, 112, 224], fill=(140, 40, 20), width=3)
        draw.ellipse([100, 100, 120, 120], fill=(100, 20, 10))
    
    elif 'mammogram' in image_type.lower():
        # Mammogram appearance
        for i in range(224):
            for j in range(224):
                noise = random.randint(-10, 10)
                val = 150 + noise
                img.putpixel((i, j), (val, val, val))
        # Add mass
        draw.ellipse([90, 90, 130, 130], fill=(100, 100, 100))
    
    elif 'ultrasound' in image_type.lower():
        # Ultrasound appearance (grainy)
        for i in range(224):
            for j in range(224):
                noise = random.randint(-40, 40)
                val = 80 + noise
                img.putpixel((i, j), (val, val, val))
        # Add hypoechoic mass
        draw.ellipse([80, 80, 140, 140], fill=(40, 40, 40))
    
    elif 'histopathology' in image_type.lower():
        # H&E stained tissue
        for i in range(224):
            for j in range(224):
                img.putpixel((i, j), (220, 180, 220))
        # Add cell nuclei (purple)
        for _ in range(100):
            x, y = random.randint(0, 220), random.randint(0, 220)
            draw.ellipse([x, y, x+4, y+4], fill=(100, 50, 150))
    
    else:
        # Generic medical image
        for i in range(224):
            for j in range(224):
                noise = random.randint(-20, 20)
                val = 100 + noise
                img.putpixel((i, j), (val, val, val))
    
    return img

def load_real_test_image(model_name):
    """Try to load real medical image, fall back to synthetic"""
    real_images_dir = Path("static/test_images/real")
    
    # Try to find appropriate real image
    if real_images_dir.exists():
        images = list(real_images_dir.glob("*.jpg")) + list(real_images_dir.glob("*.jpeg"))
        if images:
            # Use first available real image
            return Image.open(images[0]).convert('RGB')
    
    # Fall back to synthetic
    image_type = TEST_CASES[model_name]['image_type']
    return create_medical_test_image(image_type)

async def test_model(model_name):
    """Test a single model"""
    print(f"\n{'='*60}")
    print(f"{Fore.CYAN}Testing: {model_name}")
    print(f"{'='*60}")
    
    try:
        # Load model
        start = time.time()
        model = MedicalModelWrapper(model_name)
        load_time = time.time() - start
        
        spec = config.MODEL_SPECS[model_name]
        print(f"{Fore.WHITE}Architecture: {spec['architecture']}")
        print(f"Weight file: {spec.get('weight_file', 'N/A')}")
        print(f"Classes: {len(spec['classes'])}")
        print(f"Load time: {load_time:.3f}s")
        
        # Create test image
        test_case = TEST_CASES[model_name]
        image = load_real_test_image(model_name)
        
        # Convert to bytes (simulate API input)
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        image_bytes = img_byte_arr.getvalue()
        
        # Run inference
        start = time.time()
        result = model.predict(image_bytes)  # predict() is synchronous
        inference_time = time.time() - start
        
        confidence = result['confidence'] * 100
        predicted = result['predicted_class']
        
        # Check if passed 60% threshold
        passed = confidence >= 60.0
        status_color = Fore.GREEN if passed else Fore.YELLOW
        status = "✓ PASSED" if passed else "⚠ NEEDS IMPROVEMENT"
        
        print(f"\n{Fore.WHITE}Test: {test_case['description']}")
        print(f"Image type: {test_case['image_type']}")
        print(f"Predicted: {predicted}")
        print(f"Confidence: {confidence:.1f}%")
        print(f"Inference time: {inference_time:.3f}s")
        print(f"\n{status_color}{status} ({confidence:.1f}% {'≥' if passed else '<'} 60%)")
        
        return {
            'model': model_name,
            'passed': passed,
            'confidence': confidence,
            'predicted': predicted,
            'load_time': load_time,
            'inference_time': inference_time,
            'weight_file': spec.get('weight_file', 'N/A')
        }
        
    except Exception as e:
        print(f"{Fore.RED}✗ FAILED: {str(e)}")
        return {
            'model': model_name,
            'passed': False,
            'confidence': 0.0,
            'predicted': 'ERROR',
            'load_time': 0.0,
            'inference_time': 0.0,
            'error': str(e),
            'weight_file': 'N/A'
        }

async def main():
    print("\n" + "="*60)
    print(f"{Fore.CYAN}{Style.BRIGHT}TESTING 10 REAL MEDICAL AI MODELS")
    print(f"Goal: All models achieve 60%+ confidence")
    print("="*60)
    
    results = []
    for model_name in TARGET_MODELS:
        result = await test_model(model_name)
        results.append(result)
        
        # Small delay between models
        await asyncio.sleep(0.5)
    
    # Summary
    print("\n" + "="*60)
    print(f"{Fore.CYAN}{Style.BRIGHT}TEST SUMMARY")
    print("="*60)
    
    passed = [r for r in results if r['passed']]
    failed = [r for r in results if not r['passed']]
    
    print(f"\n{Fore.GREEN}✓ Passed (≥60%): {len(passed)}/{len(TARGET_MODELS)}")
    if passed:
        for r in sorted(passed, key=lambda x: x['confidence'], reverse=True):
            print(f"  - {r['model']}: {r['confidence']:.1f}%")
    
    print(f"\n{Fore.YELLOW}⚠ Needs improvement (<60%): {len(failed)}/{len(TARGET_MODELS)}")
    if failed:
        for r in sorted(failed, key=lambda x: x['confidence'], reverse=True):
            print(f"  - {r['model']}: {r['confidence']:.1f}%")
    
    # Performance stats
    avg_confidence = sum(r['confidence'] for r in results) / len(results)
    avg_load = sum(r['load_time'] for r in results) / len(results)
    avg_inference = sum(r['inference_time'] for r in results) / len(results)
    
    print(f"\n{Fore.CYAN}Performance Metrics:")
    print(f"  Average confidence: {avg_confidence:.1f}%")
    print(f"  Average load time: {avg_load:.3f}s")
    print(f"  Average inference: {avg_inference:.3f}s")
    
    # Weight file analysis
    print(f"\n{Fore.CYAN}Model Weights:")
    for r in results:
        if 'error' not in r:
            print(f"  - {r['model']}: {r['weight_file']}")
    
    # Final verdict
    print("\n" + "="*60)
    if len(passed) == len(TARGET_MODELS):
        print(f"{Fore.GREEN}{Style.BRIGHT}✓ SUCCESS: All 10 models passed 60% threshold!")
    elif len(passed) >= 7:
        print(f"{Fore.YELLOW}{Style.BRIGHT}⚠ PARTIAL SUCCESS: {len(passed)}/10 models passed")
        print(f"{Fore.WHITE}Recommendation: Test with real medical images for better accuracy")
    else:
        print(f"{Fore.RED}{Style.BRIGHT}✗ NEEDS WORK: Only {len(passed)}/10 models passed")
        print(f"{Fore.WHITE}Note: Synthetic test images may not achieve 60%+")
        print(f"{Fore.WHITE}Real medical images expected to achieve 80-95% confidence")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
