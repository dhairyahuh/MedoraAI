"""
Download 2 selected small, accurate models from HuggingFace
These models are compatible with the existing config.py specifications

Models to download:
1. Brain Tumor Classification (Swin) - matches tumor_detector config
2. Lung & Colon Cancer (ViT) - matches lung_nodule_detector config
"""
from huggingface_hub import hf_hub_download
from pathlib import Path
import torch
import sys

MODELS_DIR = Path(__file__).parent.parent / "models" / "weights"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Selected models - small, accurate, and compatible with existing config
MODELS_TO_DOWNLOAD = {
    # Brain Tumor Classification - Swin architecture (matches tumor_detector in config.py)
    # Accuracy: ~97% on test set per model page
    'Devarshi/Brain_Tumor_Classification': {
        'save_as': 'brain_tumor_swin.pth',
        'architecture': 'swin',
        'config_model': 'tumor_detector',
        'classes': ['Glioma', 'Meningioma', 'Pituitary', 'No Tumor'],
        'downloads': 262,
        'reported_accuracy': 0.97
    },
    
    # Lung & Colon Cancer - ViT architecture (matches lung_nodule_detector in config.py)
    # Accuracy: ~99% on test set per model page
    'DunnBC22/vit-base-patch16-224-in21k_lung_and_colon_cancer': {
        'save_as': 'lung_colon_cancer_vit.pth',
        'architecture': 'vit_base_patch16_224',
        'config_model': 'lung_nodule_detector',
        'classes': ['Colon Adenocarcinoma', 'Colon Normal', 'Lung Adenocarcinoma', 'Lung Normal', 'Lung Squamous Cell Carcinoma'],
        'downloads': 834,
        'reported_accuracy': 0.99
    },
}


def download_model(repo_id, save_name, model_info):
    """Download model from HuggingFace"""
    print(f"\n{'='*80}")
    print(f"Downloading: {repo_id}")
    print(f"Downloads: {model_info['downloads']}")
    print(f"Reported Accuracy: {model_info['reported_accuracy']*100:.0f}%")
    print(f"Target config: {model_info['config_model']}")
    print(f"Classes: {', '.join(model_info['classes'])}")
    print(f"{'='*80}")
    
    save_path = MODELS_DIR / save_name
    
    if save_path.exists():
        print(f"⚠ Already exists: {save_path.name}")
        size_mb = save_path.stat().st_size / (1024 * 1024)
        print(f"  Size: {size_mb:.1f} MB")
        return True, save_path
    
    try:
        # Try different file patterns
        file_patterns = [
            "pytorch_model.bin",
            "model.safetensors",
            "tf_model.h5",
        ]
        
        downloaded = False
        for pattern in file_patterns:
            try:
                print(f"Trying {pattern}...")
                model_file = hf_hub_download(
                    repo_id=repo_id,
                    filename=pattern,
                    cache_dir=str(MODELS_DIR.parent / ".cache")
                )
                
                # Load and save in our format
                if pattern.endswith('.bin'):
                    state_dict = torch.load(model_file, map_location='cpu', weights_only=False)
                    torch.save(state_dict, save_path)
                    downloaded = True
                    break
                elif pattern.endswith('.safetensors'):
                    from safetensors.torch import load_file
                    state_dict = load_file(model_file)
                    torch.save(state_dict, save_path)
                    downloaded = True
                    break
                    
            except Exception as e:
                print(f"  ✗ {pattern} not found: {str(e)[:50]}...")
                continue
        
        if not downloaded:
            print(f"✗ Could not find compatible model file")
            return False, None
            
        size_mb = save_path.stat().st_size / (1024 * 1024)
        print(f"✓ Downloaded: {save_path.name} ({size_mb:.1f} MB)")
        return True, save_path
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False, None


def test_model_loading(save_path, model_info):
    """Test that the downloaded model can be loaded"""
    print(f"\n--- Testing model loading for {save_path.name} ---")
    
    try:
        state_dict = torch.load(save_path, map_location='cpu', weights_only=False)
        
        # Check model structure
        if isinstance(state_dict, dict):
            num_params = sum(v.numel() for v in state_dict.values() if hasattr(v, 'numel'))
            print(f"✓ Model loaded successfully")
            print(f"  Total parameters: {num_params:,}")
            print(f"  Keys in state_dict: {len(state_dict)}")
            
            # Show first few keys to verify structure
            keys = list(state_dict.keys())[:5]
            print(f"  Sample keys: {keys}")
            
            return True, num_params
        else:
            print(f"✓ Model object loaded: {type(state_dict)}")
            return True, 0
            
    except Exception as e:
        print(f"✗ Error loading model: {e}")
        return False, 0


def main():
    print("="*80)
    print("DOWNLOADING SELECTED MEDICAL AI MODELS FROM HUGGINGFACE")
    print("="*80)
    print(f"\nDestination: {MODELS_DIR.absolute()}")
    print(f"Models to download: {len(MODELS_TO_DOWNLOAD)}\n")
    
    results = []
    
    for repo_id, info in MODELS_TO_DOWNLOAD.items():
        success, save_path = download_model(repo_id, info['save_as'], info)
        
        if success and save_path:
            # Test model loading
            load_success, num_params = test_model_loading(save_path, info)
            results.append({
                'repo': repo_id,
                'file': info['save_as'],
                'config_model': info['config_model'],
                'download_success': success,
                'load_success': load_success,
                'num_params': num_params,
                'reported_accuracy': info['reported_accuracy']
            })
        else:
            results.append({
                'repo': repo_id,
                'file': info['save_as'],
                'config_model': info['config_model'],
                'download_success': False,
                'load_success': False,
                'num_params': 0,
                'reported_accuracy': info['reported_accuracy']
            })
    
    # Summary
    print("\n" + "="*80)
    print("DOWNLOAD & TEST SUMMARY")
    print("="*80)
    
    for r in results:
        status = "✓" if r['download_success'] and r['load_success'] else "✗"
        print(f"\n{status} {r['file']}")
        print(f"   Source: {r['repo']}")
        print(f"   Config Model: {r['config_model']}")
        print(f"   Reported Accuracy: {r['reported_accuracy']*100:.0f}%")
        if r['num_params'] > 0:
            print(f"   Parameters: {r['num_params']:,}")
    
    success_count = sum(1 for r in results if r['download_success'] and r['load_success'])
    print(f"\n{'='*80}")
    print(f"Total: {success_count}/{len(results)} models ready for use")
    
    if success_count > 0:
        print("\n📋 Next Steps:")
        print("1. Models are saved to models/weights/")
        print("2. Update config.py weight_file paths if different")
        print("3. For accuracy testing, you can use the existing model infrastructure")
    
    return success_count == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
