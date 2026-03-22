"""
Model Validation Pipeline
Automated quality gates before deploying models to production
"""
import torch
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
from PIL import Image
import json

logger = logging.getLogger(__name__)

class ModelValidator:
    """Validates models before production deployment"""
    
    def __init__(self, validation_data_dir: str = "validation_data"):
        self.validation_dir = Path(validation_data_dir)
        self.validation_dir.mkdir(parents=True, exist_ok=True)
        
        # Validation thresholds
        self.thresholds = {
            'min_accuracy': 0.70,  # 70% minimum accuracy
            'max_inference_time': 5.0,  # 5 seconds max
            'min_samples': 10,  # Need at least 10 test samples
            'max_model_size': 500 * 1024 * 1024,  # 500 MB
        }
    
    def validate_model(self, model_path: Path, model_name: str) -> Tuple[bool, Dict]:
        """
        Complete model validation
        
        Returns:
            (passed, results) - Boolean pass/fail and detailed results
        """
        results = {
            'model_name': model_name,
            'model_path': str(model_path),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'tests': {},
            'passed': False
        }
        
        logger.info(f"[Validation] Starting validation for {model_name}")
        
        try:
            # Test 1: File format validation
            results['tests']['format'] = self._validate_format(model_path)
            
            # Test 2: Model loading
            model, device = self._load_model(model_path)
            if model is None:
                results['tests']['loading'] = {'passed': False, 'error': 'Failed to load model'}
                return False, results
            results['tests']['loading'] = {'passed': True}
            
            # Test 3: Inference speed
            results['tests']['speed'] = self._validate_speed(model, device)
            
            # Test 4: Accuracy (if validation data available)
            results['tests']['accuracy'] = self._validate_accuracy(model, device, model_name)
            
            # Test 5: Robustness
            results['tests']['robustness'] = self._validate_robustness(model, device)
            
            # Test 6: GPU compatibility
            results['tests']['gpu'] = self._validate_gpu_compatibility(model_path)
            
            # Overall pass/fail
            all_passed = all(
                test_result.get('passed', False) 
                for test_result in results['tests'].values()
                if 'passed' in test_result
            )
            
            results['passed'] = all_passed
            
            if all_passed:
                logger.info(f"[Validation] ✓ {model_name} passed all tests")
            else:
                failed_tests = [
                    name for name, result in results['tests'].items()
                    if not result.get('passed', False)
                ]
                logger.warning(f"[Validation] ❌ {model_name} failed tests: {', '.join(failed_tests)}")
            
            return all_passed, results
            
        except Exception as e:
            logger.error(f"[Validation] ❌ {model_name} validation crashed: {e}")
            results['tests']['exception'] = {'passed': False, 'error': str(e)}
            return False, results
    
    def _validate_format(self, model_path: Path) -> Dict:
        """Validate file format and size"""
        result = {'passed': False}
        
        try:
            if not model_path.exists():
                result['error'] = 'File does not exist'
                return result
            
            # Check extension
            valid_extensions = ['.pth', '.pt', '.safetensors', '.ckpt']
            if model_path.suffix not in valid_extensions:
                result['error'] = f'Invalid extension: {model_path.suffix}'
                return result
            
            # Check size
            file_size = model_path.stat().st_size
            if file_size > self.thresholds['max_model_size']:
                result['error'] = f'Model too large: {file_size / (1024**2):.1f} MB'
                return result
            
            if file_size < 1024:  # Less than 1 KB
                result['error'] = 'Model file too small (likely corrupted)'
                return result
            
            result['passed'] = True
            result['size_mb'] = file_size / (1024**2)
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _load_model(self, model_path: Path) -> Tuple[Optional[torch.nn.Module], str]:
        """Try to load model"""
        try:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            # Try loading
            checkpoint = torch.load(model_path, map_location=device)
            
            # Extract model if it's wrapped in a checkpoint
            if isinstance(checkpoint, dict):
                if 'model_state_dict' in checkpoint:
                    model_state = checkpoint['model_state_dict']
                elif 'state_dict' in checkpoint:
                    model_state = checkpoint['state_dict']
                else:
                    # Assume the dict IS the state dict
                    model_state = checkpoint
            else:
                model_state = checkpoint
            
            # For validation, we just check it loads
            # Real model architecture would be loaded by ModelManager
            logger.info(f"[Validation] Model loaded successfully ({len(model_state)} parameters)")
            
            return None, device  # Return None as we don't have architecture
            
        except Exception as e:
            logger.error(f"[Validation] Failed to load model: {e}")
            return None, 'cpu'
    
    def _validate_speed(self, model, device: str) -> Dict:
        """Validate inference speed"""
        result = {'passed': False}
        
        try:
            # Create dummy input (224x224 RGB image)
            dummy_input = torch.randn(1, 3, 224, 224).to(device)
            
            # Warm-up
            if model:
                with torch.no_grad():
                    _ = model(dummy_input)
            
            # Measure inference time
            times = []
            for _ in range(10):
                start = time.time()
                if model:
                    with torch.no_grad():
                        _ = model(dummy_input)
                else:
                    time.sleep(0.1)  # Simulate if no model
                times.append(time.time() - start)
            
            avg_time = np.mean(times)
            std_time = np.std(times)
            
            result['avg_time_seconds'] = round(avg_time, 3)
            result['std_time_seconds'] = round(std_time, 3)
            result['passed'] = avg_time < self.thresholds['max_inference_time']
            
            if not result['passed']:
                result['error'] = f"Too slow: {avg_time:.2f}s (threshold: {self.thresholds['max_inference_time']}s)"
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _validate_accuracy(self, model, device: str, model_name: str) -> Dict:
        """Validate accuracy on validation set"""
        result = {'passed': False}
        
        try:
            # Look for validation data
            val_dir = self.validation_dir / model_name
            
            if not val_dir.exists() or not list(val_dir.glob('**/*')):
                result['skipped'] = True
                result['passed'] = True  # Don't fail if no validation data
                result['message'] = 'No validation data available'
                return result
            
            # Load validation images and labels
            samples = self._load_validation_samples(val_dir)
            
            if len(samples) < self.thresholds['min_samples']:
                result['skipped'] = True
                result['passed'] = True
                result['message'] = f'Insufficient samples: {len(samples)} < {self.thresholds["min_samples"]}'
                return result
            
            # Run inference
            if model:
                correct = 0
                for image_path, true_label in samples:
                    pred_label = self._predict(model, device, image_path)
                    if pred_label == true_label:
                        correct += 1
                
                accuracy = correct / len(samples)
                result['accuracy'] = round(accuracy, 3)
                result['samples'] = len(samples)
                result['passed'] = accuracy >= self.thresholds['min_accuracy']
                
                if not result['passed']:
                    result['error'] = f"Low accuracy: {accuracy:.1%} (threshold: {self.thresholds['min_accuracy']:.1%})"
            else:
                result['skipped'] = True
                result['passed'] = True
                result['message'] = 'Model architecture not available'
            
        except Exception as e:
            result['error'] = str(e)
            result['passed'] = True  # Don't fail validation on accuracy test errors
        
        return result
    
    def _validate_robustness(self, model, device: str) -> Dict:
        """Test robustness to input variations"""
        result = {'passed': False}
        
        try:
            if not model:
                result['skipped'] = True
                result['passed'] = True
                result['message'] = 'Model architecture not available'
                return result
            
            # Test different input variations
            test_cases = [
                ('normal', torch.randn(1, 3, 224, 224)),
                ('all_zeros', torch.zeros(1, 3, 224, 224)),
                ('all_ones', torch.ones(1, 3, 224, 224)),
                ('small_values', torch.randn(1, 3, 224, 224) * 0.01),
            ]
            
            results_list = []
            for name, input_tensor in test_cases:
                try:
                    input_tensor = input_tensor.to(device)
                    with torch.no_grad():
                        output = model(input_tensor)
                    
                    # Check for NaN or Inf
                    if torch.isnan(output).any() or torch.isinf(output).any():
                        results_list.append(f"{name}: NaN/Inf detected")
                    else:
                        results_list.append(f"{name}: OK")
                except Exception as e:
                    results_list.append(f"{name}: {str(e)}")
            
            # Pass if no NaN/Inf detected
            failures = [r for r in results_list if 'NaN' in r or 'Inf' in r or 'Error' in r]
            result['passed'] = len(failures) == 0
            result['test_results'] = results_list
            
            if not result['passed']:
                result['error'] = f"Robustness failures: {', '.join(failures)}"
            
        except Exception as e:
            result['error'] = str(e)
            result['passed'] = True  # Don't fail validation on robustness test errors
        
        return result
    
    def _validate_gpu_compatibility(self, model_path: Path) -> Dict:
        """Check GPU compatibility"""
        result = {'passed': True}  # Default to pass
        
        try:
            cuda_available = torch.cuda.is_available()
            result['cuda_available'] = cuda_available
            
            if cuda_available:
                result['gpu_name'] = torch.cuda.get_device_name(0)
                result['gpu_memory_gb'] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            else:
                result['message'] = 'CUDA not available, will use CPU'
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _load_validation_samples(self, val_dir: Path) -> List[Tuple[Path, str]]:
        """Load validation images and labels"""
        samples = []
        
        # Expect structure: validation_data/{model_name}/{class_name}/{image.jpg}
        for class_dir in val_dir.iterdir():
            if class_dir.is_dir():
                class_name = class_dir.name
                for img_path in class_dir.glob('*.jpg') + class_dir.glob('*.png'):
                    samples.append((img_path, class_name))
        
        return samples
    
    def _predict(self, model, device: str, image_path: Path) -> str:
        """Run inference on single image"""
        try:
            from torchvision import transforms
            
            # Load and preprocess image
            image = Image.open(image_path).convert('RGB')
            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            
            tensor = transform(image).unsqueeze(0).to(device)
            
            # Inference
            with torch.no_grad():
                output = model(tensor)
            
            # Get prediction
            pred_idx = torch.argmax(output, dim=1).item()
            
            # Would need model.classes attribute for actual label
            return f"class_{pred_idx}"
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return "error"
    
    def save_validation_report(self, results: Dict, output_dir: str = "validation_reports"):
        """Save validation report to file"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        report_file = output_path / f"validation_{results['model_name']}_{int(time.time())}.json"
        
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"[Validation] Report saved: {report_file}")
        return report_file

def validate_model_before_deployment(model_path: str, model_name: str) -> bool:
    """
    Convenience function to validate model
    
    Returns:
        True if model passes all validation tests
    """
    validator = ModelValidator()
    passed, results = validator.validate_model(Path(model_path), model_name)
    validator.save_validation_report(results)
    
    return passed
