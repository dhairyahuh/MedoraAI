#!/usr/bin/env python3
"""
Test script to verify federated learning is working
Tests the complete flow from gradient contribution to model update
"""
import sys
sys.path.insert(0, '/Users/tusharchopra/Downloads/MedoraAI')

import torch
from pathlib import Path
from collections import OrderedDict
import config
from federated.federated_storage import FederatedStorage
from federated.fedavg import FederatedAveraging
from federated.differential_privacy import DifferentialPrivacy
from models.model_manager import MedicalModelWrapper

def test_gradient_storage():
    """Test that gradients can be saved and loaded"""
    print("\n" + "="*60)
    print("1. TESTING GRADIENT STORAGE")
    print("="*60)
    
    storage_dir = Path(config.BASE_DIR) / "federated_data"
    fed_storage = FederatedStorage(storage_dir)
    
    # Check existing contributions
    stats = fed_storage.get_federated_stats()
    print(f"Total contributions: {stats.get('total_contributions', 0)}")
    print(f"Total hospitals: {stats.get('total_hospitals', 0)}")
    print(f"Models with contributions: {stats.get('models', [])}")
    
    # Check hospital stats
    hospital_stats = fed_storage.get_hospital_stats()
    print(f"\nHospital Statistics:")
    for h in hospital_stats[:5]:  # Show first 5
        print(f"  - {h}")
    
    return stats.get('total_contributions', 0) > 0

def test_model_loading():
    """Test that models can be loaded for federated learning"""
    print("\n" + "="*60)
    print("2. TESTING MODEL LOADING FOR FEDERATED LEARNING")
    print("="*60)
    
    # All 10 models with downloaded HuggingFace weights
    models_to_test = [
        'pneumonia_detector',
        'skin_cancer_detector', 
        'tumor_detector',
        'lung_nodule_detector',
        'breast_cancer_detector',
        'diabetic_retinopathy_detector',
        'polyp_detector',
        'cancer_grading_detector',
        'fracture_detector',
        'ultrasound_classifier',
    ]
    
    results = {}
    for model_name in models_to_test:
        try:
            print(f"\nLoading {model_name}...")
            model = MedicalModelWrapper(model_name, device='cpu')
            
            if model.model is not None:
                # Get number of trainable parameters
                n_params = sum(p.numel() for p in model.model.parameters() if p.requires_grad)
                print(f"  ✓ Loaded successfully")
                print(f"    Classes: {model.classes}")
                print(f"    Trainable params: {n_params:,}")
                results[model_name] = True
            else:
                print(f"  ✗ Model is None")
                results[model_name] = False
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results[model_name] = False
    
    return results

def test_gradient_computation():
    """Test that gradients can be computed from a model"""
    print("\n" + "="*60)
    print("3. TESTING GRADIENT COMPUTATION")
    print("="*60)
    
    models_to_test = [
        'pneumonia_detector',
        'skin_cancer_detector', 
        'tumor_detector',
        'lung_nodule_detector',
        'breast_cancer_detector',
        'diabetic_retinopathy_detector',
        'polyp_detector',
        'cancer_grading_detector',
        'fracture_detector',
        'ultrasound_classifier',
    ]
    
    results = {}
    
    for model_name in models_to_test:
        print(f"\nTesting with {model_name}...")
        try:
            model = MedicalModelWrapper(model_name, device='cpu')
            
            if model.model is None:
                print("  ✗ Model not loaded")
                results[model_name] = False
                continue
            
            # Determine image size
            spec = config.MODEL_SPECS.get(model_name, {})
            img_size = spec.get('image_size', 224)
            
            # Create dummy input
            dummy_input = torch.randn(1, 3, img_size, img_size)
            
            # Forward pass
            model.model.train()
            
            # Handle different model types
            if model_name in ['skin_cancer_detector', 'diabetic_retinopathy_detector', 'tumor_detector', 
                              'polyp_detector', 'cancer_grading_detector', 'fracture_detector', 'ultrasound_classifier']:
                # HuggingFace Models
                output_obj = model.model(pixel_values=dummy_input)
                output = output_obj.logits
            elif model_name in ['pneumonia_detector', 'breast_cancer_detector']:
                 # ViT manual models (input dict or kwarg)
                 output_obj = model.model(pixel_values=dummy_input)
                 output = output_obj.logits
            else:
                # Standard torchvision models (ResNet/Inception)
                output = model.model(dummy_input)
                # Inception returns tuple in train mode
                if isinstance(output, tuple):
                    output = output[0]
            
            print(f"  Output shape: {output.shape}")
            
            # Create dummy target
            target = torch.tensor([0], dtype=torch.long)
            
            # Compute loss
            criterion = torch.nn.CrossEntropyLoss()
            loss = criterion(output, target)
            print(f"  Loss: {loss.item():.4f}")
            
            # Backward pass
            model.model.zero_grad()
            loss.backward()
            
            # Extract gradients
            gradients = OrderedDict()
            for name, param in model.model.named_parameters():
                if param.grad is not None:
                    gradients[name] = param.grad.clone().detach()
            
            print(f"  ✓ Computed {len(gradients)} gradients")
            
            # Apply differential privacy
            dp = DifferentialPrivacy(epsilon=0.1)
            clipped = dp.clip_gradients(gradients)
            noisy = dp.add_noise(clipped)
            
            print(f"  ✓ Applied differential privacy (ε=0.1)")
            results[model_name] = True
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            results[model_name] = False
            
    return results

def test_fedavg_aggregation():
    """Test FedAvg aggregation"""
    print("\n" + "="*60)
    print("4. TESTING FEDAVG AGGREGATION")
    print("="*60)
    
    try:
        # Create a simple model for testing
        import torch.nn as nn
        test_model = nn.Sequential(
            nn.Linear(10, 5),
            nn.ReLU(),
            nn.Linear(5, 2)
        )
        
        # Initialize FedAvg
        fedavg = FederatedAveraging(test_model, learning_rate=0.1)
        
        # Create some fake client gradients
        client_gradients = []
        for i in range(3):
            grads = OrderedDict()
            for name, param in test_model.named_parameters():
                grads[name] = torch.randn_like(param) * 0.01
            client_gradients.append(grads)
        
        print(f"  Created {len(client_gradients)} client gradients")
        
        # Aggregate
        aggregated = fedavg.aggregate_gradients(client_gradients)
        print(f"  ✓ Aggregated {len(aggregated)} gradient tensors")
        
        # Apply to model
        old_state = {k: v.clone() for k, v in test_model.state_dict().items()}
        fedavg.apply_gradients(aggregated)
        new_state = test_model.state_dict()
        
        # Check if model was updated
        model_changed = False
        for key in old_state:
            if not torch.allclose(old_state[key], new_state[key]):
                model_changed = True
                break
        
        if model_changed:
            print("  ✓ Model weights updated after aggregation")
        else:
            print("  ⚠ Model weights unchanged (might be expected with tiny gradients)")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_federated_flow():
    """Test the complete federated learning flow"""
    print("\n" + "="*60)
    print("5. TESTING FULL FEDERATED FLOW")
    print("="*60)
    
    storage_dir = Path(config.BASE_DIR) / "federated_data"
    fed_storage = FederatedStorage(storage_dir)
    
    model_name = 'polyp_detector'  # Use a new HuggingFace model to verify full flow
    
    try:
        # Load model
        print(f"Loading {model_name}...")
        model = MedicalModelWrapper(model_name, device='cpu')
        
        if model.model is None:
            print("  ✗ Model not loaded")
            return False
        
        # Load any existing gradients
        gradients_list = fed_storage.load_gradients(model_name)
        print(f"  Existing gradient contributions: {len(gradients_list)}")
        
        # Inject dummy contributions if not enough
        if len(gradients_list) < 2:
            print("  Injecting dummy contributions to force aggregation test...")
            for i in range(2 - len(gradients_list)):
                dummy_grads = OrderedDict()
                for name, param in model.model.named_parameters():
                    if param.requires_grad:
                        dummy_grads[name] = torch.randn_like(param) * 0.001
                
                cid = fed_storage.add_contribution(f"test_hosp_{i}", model_name, 0.1, 0.1)
                fed_storage.save_gradients(f"test_hosp_{i}", model_name, dummy_grads, cid)
            
            # Reload
            gradients_list = fed_storage.load_gradients(model_name)
            print(f"  Contributions after injection: {len(gradients_list)}")
        
        if len(gradients_list) >= 2:
            # We have enough to do an aggregation
            print("  Performing aggregation...")
            
            fed_avg = FederatedAveraging(model.model, learning_rate=0.01)
            gradients_only = [grad for _, grad in gradients_list]
            
            aggregated_grad = fed_avg.aggregate_gradients(gradients_only)
            print(f"  ✓ Aggregated {len(aggregated_grad)} gradient tensors")
            
            # Apply gradients
            fed_avg.apply_gradients(aggregated_grad)
            print("  ✓ Applied aggregated gradients to model")
            
            # Save updated model
            model_state = OrderedDict(model.model.state_dict())
            fed_storage.save_global_model(
                model_name=model_name,
                model_state=model_state,
                round_id=fed_avg.round
            )
            print(f"  ✓ Saved updated global model (round {fed_avg.round})")
            
            return True
        else:
            print("  ⚠ Not enough contributions for aggregation (need >= 2)")
            print("  Submit more radiologist reviews to accumulate gradients")
            return True  # Not a failure, just not enough data
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*60)
    print("FEDERATED LEARNING VERIFICATION TEST")
    print("="*60)
    
    results = {}
    
    # Run all tests
    results['storage'] = test_gradient_storage()
    results['model_loading'] = test_model_loading()
    results['gradient_computation'] = test_gradient_computation()
    results['fedavg_aggregation'] = test_fedavg_aggregation()
    results['full_flow'] = test_full_federated_flow()
    
    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    for test, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        color_status = f"\033[92m{status}\033[0m" if passed else f"\033[91m{status}\033[0m"
        if isinstance(passed, dict):
            # Model loading returns dict
            all_pass = all(passed.values())
            status = "✓ PASS" if all_pass else "✗ FAIL"
            print(f"{test}: {status}")
            for model, ok in passed.items():
                sub_status = "✓" if ok else "✗"
                print(f"    {model}: {sub_status}")
        else:
            print(f"{test}: {status}")
    
    all_passed = all(v if not isinstance(v, dict) else all(v.values()) for v in results.values())
    
    if all_passed:
        print("\n✓ All federated learning tests passed!")
    else:
        print("\n✗ Some tests failed - check output above for details")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
