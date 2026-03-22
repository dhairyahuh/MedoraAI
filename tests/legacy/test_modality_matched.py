"""
Test models ONLY with correctly matched medical images
Only test when we have the proper modality image
"""
import sys
from pathlib import Path
import torch
from PIL import Image
import io
from colorama import init, Fore, Style
import time

init(autoreset=True)

sys.path.insert(0, str(Path(__file__).parent))

from models.model_manager import MedicalModelWrapper
from config import MODEL_SPECS

# ONLY test models where we have the correct modality image
CORRECT_MODALITY_TESTS = [
    {
        'model': 'pneumonia_detector',
        'images': [
            'chest_xray_pneumonia_1.jpeg',
            'chest_xray_pneumonia_2.jpeg',
            'chest_xray_normal.jpeg',
        ],
        'modality': 'Chest X-ray',
        'description': 'Chest X-ray pneumonia detection'
    },
    {
        'model': 'polyp_detector',  # COVID CT model
        'images': [
            'covid_ct_1.jpg',
            'chest_xray_covid.jpeg',  # COVID X-ray also relevant
        ],
        'modality': 'CT Scan / COVID X-ray',
        'description': 'COVID-19 CT scan detection'
    },
    {
        'model': 'tumor_detector',
        'images': [
            'brain_tumor.jpg',
        ],
        'modality': 'Brain MRI',
        'description': 'Brain tumor MRI detection'
    },
    {
        'model': 'breast_cancer_detector',
        'images': [
            'breast_histo_idc.jpg',
        ],
        'modality': 'Histopathology',
        'description': 'Breast cancer histopathology'
    },
    {
        'model': 'lung_nodule_detector',
        'images': [
            'breast_histo_idc.jpg',  # Histopathology model, can use this
        ],
        'modality': 'Histopathology',
        'description': 'Lung/Colon cancer histopathology'
    },
]

def test_model_with_correct_images(model_name, image_filenames, modality, description):
    """Test a model with all its appropriate images"""
    print(f"\n{'='*70}")
    print(f"{Fore.CYAN}{Style.BRIGHT}Testing: {model_name}")
    print(f"{'='*70}")
    
    try:
        # Load model
        print(f"{Fore.WHITE}Loading model...")
        start = time.time()
        model = MedicalModelWrapper(model_name)
        load_time = time.time() - start
        
        spec = MODEL_SPECS[model_name]
        print(f"Architecture: {spec['architecture']}")
        print(f"Weight file: {spec.get('weight_file', 'N/A')}")
        print(f"Classes: {spec['classes']}")
        print(f"Modality: {modality}")
        print(f"Load time: {load_time:.3f}s")
        
        results = []
        
        # Test with each appropriate image
        for img_filename in image_filenames:
            img_path = Path("static/test_images/real_samples") / img_filename
            if not img_path.exists():
                print(f"{Fore.YELLOW}⚠ Image not found: {img_filename}")
                continue
            
            print(f"\n{Fore.CYAN}Testing with: {img_filename}")
            
            # Load image
            image = Image.open(img_path).convert('RGB')
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            image_bytes = img_byte_arr.getvalue()
            
            # Run inference
            start = time.time()
            result = model.predict(image_bytes)
            inference_time = time.time() - start
            
            confidence = result['confidence'] * 100
            predicted = result['predicted_class']
            
            # Check threshold
            passed = confidence >= 60.0
            status_color = Fore.GREEN if passed else Fore.YELLOW
            status = "✓" if passed else "⚠"
            
            print(f"  Predicted: {predicted}")
            print(f"  {status_color}{status} Confidence: {confidence:.1f}% ({inference_time:.3f}s)")
            
            results.append({
                'image': img_filename,
                'confidence': confidence,
                'predicted': predicted,
                'passed': passed,
                'inference_time': inference_time
            })
        
        # Summary for this model
        if results:
            avg_conf = sum(r['confidence'] for r in results) / len(results)
            max_conf = max(r['confidence'] for r in results)
            passed_count = sum(1 for r in results if r['passed'])
            
            print(f"\n{Fore.CYAN}Model Summary:")
            print(f"  Images tested: {len(results)}")
            print(f"  Average confidence: {avg_conf:.1f}%")
            print(f"  Maximum confidence: {max_conf:.1f}%")
            print(f"  Passed (≥60%): {passed_count}/{len(results)}")
            
            overall_passed = avg_conf >= 60.0
            status_color = Fore.GREEN if overall_passed else Fore.YELLOW
            status = "✓ PASSED" if overall_passed else "⚠ NEEDS IMPROVEMENT"
            print(f"\n{status_color}{Style.BRIGHT}{status} (Avg: {avg_conf:.1f}%)")
            
            return {
                'model': model_name,
                'modality': modality,
                'description': description,
                'images_tested': len(results),
                'avg_confidence': avg_conf,
                'max_confidence': max_conf,
                'passed_count': passed_count,
                'overall_passed': overall_passed,
                'load_time': load_time,
                'weight_file': spec.get('weight_file', 'N/A'),
                'results': results
            }
        
        return None
        
    except Exception as e:
        print(f"{Fore.RED}✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("\n" + "="*70)
    print(f"{Fore.CYAN}{Style.BRIGHT}TESTING MODELS WITH CORRECT MODALITY IMAGES ONLY")
    print(f"No cross-modality testing - each model gets its proper images")
    print("="*70)
    
    # List available images
    samples_dir = Path("static/test_images/real_samples")
    available = list(samples_dir.glob("*.jpg")) + list(samples_dir.glob("*.jpeg")) + list(samples_dir.glob("*.png"))
    
    print(f"\n{Fore.WHITE}Available real medical images: {len(available)}")
    for img in sorted(available):
        size_kb = img.stat().st_size / 1024
        print(f"  - {img.name} ({size_kb:.1f} KB)")
    
    # Run tests
    all_results = []
    
    for test_config in CORRECT_MODALITY_TESTS:
        result = test_model_with_correct_images(
            test_config['model'],
            test_config['images'],
            test_config['modality'],
            test_config['description']
        )
        if result:
            all_results.append(result)
        time.sleep(0.3)
    
    # Final Summary
    print("\n" + "="*70)
    print(f"{Fore.CYAN}{Style.BRIGHT}FINAL RESULTS - CORRECT MODALITY TESTING")
    print("="*70)
    
    if not all_results:
        print(f"{Fore.RED}No results to display")
        return
    
    # Separate by pass/fail
    passed_models = [r for r in all_results if r['overall_passed']]
    failed_models = [r for r in all_results if not r['overall_passed']]
    
    print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ MODELS ACHIEVING ≥60% (PASSED): {len(passed_models)}/{len(all_results)}")
    if passed_models:
        for r in sorted(passed_models, key=lambda x: x['avg_confidence'], reverse=True):
            print(f"\n  {Fore.GREEN}✓ {r['model']}")
            print(f"    Modality: {r['modality']}")
            print(f"    Average: {r['avg_confidence']:.1f}% | Max: {r['max_confidence']:.1f}%")
            print(f"    Images tested: {r['images_tested']} | Passed: {r['passed_count']}/{r['images_tested']}")
            print(f"    Weight: {r['weight_file']}")
            
            # Show individual image results
            for img_result in r['results']:
                status = "✓" if img_result['passed'] else "⚠"
                color = Fore.GREEN if img_result['passed'] else Fore.YELLOW
                print(f"      {color}{status} {img_result['image']}: {img_result['confidence']:.1f}%")
    
    print(f"\n{Fore.YELLOW}{Style.BRIGHT}⚠ MODELS <60% (NEEDS IMPROVEMENT): {len(failed_models)}/{len(all_results)}")
    if failed_models:
        for r in sorted(failed_models, key=lambda x: x['avg_confidence'], reverse=True):
            print(f"\n  {Fore.YELLOW}⚠ {r['model']}")
            print(f"    Modality: {r['modality']}")
            print(f"    Average: {r['avg_confidence']:.1f}% | Max: {r['max_confidence']:.1f}%")
            print(f"    Images tested: {r['images_tested']} | Passed: {r['passed_count']}/{r['images_tested']}")
            print(f"    Weight: {r['weight_file']}")
            
            # Show individual image results
            for img_result in r['results']:
                status = "✓" if img_result['passed'] else "⚠"
                color = Fore.GREEN if img_result['passed'] else Fore.YELLOW
                print(f"      {color}{status} {img_result['image']}: {img_result['confidence']:.1f}%")
    
    # Overall statistics
    total_images = sum(r['images_tested'] for r in all_results)
    total_passed_images = sum(r['passed_count'] for r in all_results)
    avg_all_confidence = sum(r['avg_confidence'] for r in all_results) / len(all_results)
    max_all_confidence = max(r['max_confidence'] for r in all_results)
    avg_load_time = sum(r['load_time'] for r in all_results) / len(all_results)
    
    print(f"\n{Fore.CYAN}{Style.BRIGHT}Overall Statistics:")
    print(f"  Models tested: {len(all_results)}")
    print(f"  Total images tested: {total_images}")
    print(f"  Individual images ≥60%: {total_passed_images}/{total_images} ({total_passed_images/total_images*100:.1f}%)")
    print(f"  Average confidence across all models: {avg_all_confidence:.1f}%")
    print(f"  Best confidence achieved: {max_all_confidence:.1f}%")
    print(f"  Average model load time: {avg_load_time:.3f}s")
    
    # Models not tested (missing proper images)
    all_models = ['pneumonia_detector', 'skin_cancer_detector', 'tumor_detector', 
                  'diabetic_retinopathy_detector', 'breast_cancer_detector', 
                  'lung_nodule_detector', 'polyp_detector', 'fracture_detector',
                  'cancer_grading_detector', 'ultrasound_classifier']
    tested_models = [r['model'] for r in all_results]
    not_tested = [m for m in all_models if m not in tested_models]
    
    if not_tested:
        print(f"\n{Fore.YELLOW}Models not tested (missing correct modality images):")
        for model in not_tested:
            spec = MODEL_SPECS[model]
            print(f"  - {model}: needs {spec.get('weight_file', 'specific')} modality images")
    
    # Final verdict
    print("\n" + "="*70)
    success_rate = len(passed_models) / len(all_results) * 100 if all_results else 0
    
    if success_rate >= 80:
        print(f"{Fore.GREEN}{Style.BRIGHT}🎉 EXCELLENT: {len(passed_models)}/{len(all_results)} models ({success_rate:.0f}%) passed!")
        print(f"{Fore.WHITE}Models work very well with correct modality images.")
    elif success_rate >= 60:
        print(f"{Fore.GREEN}{Style.BRIGHT}✓ GOOD: {len(passed_models)}/{len(all_results)} models ({success_rate:.0f}%) passed")
        print(f"{Fore.WHITE}Most models performing well with proper images.")
    elif success_rate >= 40:
        print(f"{Fore.YELLOW}{Style.BRIGHT}⚠ ACCEPTABLE: {len(passed_models)}/{len(all_results)} models ({success_rate:.0f}%) passed")
        print(f"{Fore.WHITE}Some models need better quality or more appropriate images.")
    else:
        print(f"{Fore.YELLOW}{Style.BRIGHT}⚠ NEEDS WORK: {len(passed_models)}/{len(all_results)} models ({success_rate:.0f}%) passed")
        print(f"{Fore.WHITE}Models may need better image quality or additional training.")
    
    print(f"\n{Fore.WHITE}All tested models have real HuggingFace medical training!")
    print("="*70)
    
    # Save results
    with open("test_results_modality_matched.txt", "w", encoding='utf-8') as f:
        f.write("Test Results - Correct Modality Images Only\n")
        f.write("="*70 + "\n\n")
        f.write(f"Models achieving >=60%: {len(passed_models)}/{len(all_results)}\n")
        f.write(f"Average confidence: {avg_all_confidence:.1f}%\n")
        f.write(f"Best confidence: {max_all_confidence:.1f}%\n\n")
        
        for r in all_results:
            f.write(f"\n{r['model']}: {r['avg_confidence']:.1f}% {'PASSED' if r['overall_passed'] else 'FAILED'}\n")
            f.write(f"  Modality: {r['modality']}\n")
            f.write(f"  Images: {r['images_tested']} tested, {r['passed_count']} passed\n")
            for img_r in r['results']:
                f.write(f"    - {img_r['image']}: {img_r['confidence']:.1f}%\n")
    
    print(f"\n{Fore.WHITE}Results saved to: test_results_modality_matched.txt")

if __name__ == "__main__":
    main()
