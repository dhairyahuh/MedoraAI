"""
Download additional real medical AI models from HuggingFace
Based on search results - top models by downloads
"""
from huggingface_hub import hf_hub_download
from pathlib import Path
from tqdm import tqdm
import torch

MODELS_DIR = Path("models/weights")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# High-priority models to download (verified medical AI with good downloads)
MODELS_TO_DOWNLOAD = {
    # Brain Tumor Detection
    'andrei-teodor/vit-base-brain-mri': {
        'save_as': 'brain_tumor_vit.pth',
        'architecture': 'vit_base_patch16_224',
        'classes': ['glioma', 'meningioma', 'pituitary', 'notumor'],
        'downloads': 327
    },
    
    # Chest X-ray / Pneumonia (alternative)
    'dima806/chest_xray_pneumonia_detection': {
        'save_as': 'pneumonia_detector_vit2.pth',
        'architecture': 'vit_base_patch16_224',
        'classes': ['NORMAL', 'PNEUMONIA'],
        'downloads': 1231
    },
    
    # Diabetic Retinopathy
    'AsmaaElnagger/Diabetic_RetinoPathy_detection': {
        'save_as': 'diabetic_retinopathy_dinov2.pth',
        'architecture': 'dinov2_vits14',
        'classes': ['No_DR', 'Mild', 'Moderate', 'Severe', 'Proliferate_DR'],
        'downloads': 91
    },
    
    # Breast Cancer
    'Falah/vit-base-breast-cancer': {
        'save_as': 'breast_cancer_vit.pth',
        'architecture': 'vit_base_patch16_224',
        'classes': ['benign', 'malignant', 'normal'],
        'downloads': 244
    },
    
    # Lung & Colon Cancer
    'DunnBC22/vit-base-patch16-224-in21k_lung_and_colon_cancer': {
        'save_as': 'lung_colon_cancer_vit.pth',
        'architecture': 'vit_base_patch16_224',
        'classes': ['colon_aca', 'colon_n', 'lung_aca', 'lung_n', 'lung_scc'],
        'downloads': 834
    },
    
    # Bone Fracture Detection
    'prithivMLmods/Bone-Fracture-Detection': {
        'save_as': 'bone_fracture_siglip.pth',
        'architecture': 'siglip',
        'classes': ['Elbow positive', 'Finger positive', 'Hand positive', 'Shoulder positive', 'Wrist positive', 'Negative'],
        'downloads': 997
    },
    
    # CT Scan COVID-19
    'DunnBC22/vit-base-patch16-224-in21k_covid_19_ct_scans': {
        'save_as': 'covid_ct_vit.pth',
        'architecture': 'vit_base_patch16_224',
        'classes': ['COVID-19', 'Normal'],
        'downloads': 249
    },
}

def download_model(repo_id, save_name, model_info):
    """Download model from HuggingFace"""
    print(f"\n{'='*80}")
    print(f"Downloading: {repo_id}")
    print(f"Downloads: {model_info['downloads']}")
    print(f"Classes: {', '.join(model_info['classes'][:3])}...")
    print(f"{'='*80}")
    
    save_path = MODELS_DIR / save_name
    
    if save_path.exists():
        print(f"⚠ Already exists: {save_path.name}")
        return False
    
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
                    cache_dir=".cache"
                )
                
                # Load and save in our format
                if pattern.endswith('.bin'):
                    state_dict = torch.load(model_file, map_location='cpu')
                    torch.save(state_dict, save_path)
                elif pattern.endswith('.safetensors'):
                    from safetensors.torch import load_file
                    state_dict = load_file(model_file)
                    torch.save(state_dict, save_path)
                
                size_mb = save_path.stat().st_size / (1024 * 1024)
                print(f"✓ Downloaded: {save_path.name} ({size_mb:.1f} MB)")
                downloaded = True
                break
                
            except Exception as e:
                print(f"  ✗ {pattern} not found")
                continue
        
        if not downloaded:
            print(f"✗ Could not find compatible model file")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("="*80)
    print("DOWNLOADING REAL MEDICAL AI MODELS FROM HUGGINGFACE")
    print("="*80)
    print(f"\nDestination: {MODELS_DIR.absolute()}")
    print(f"Models to download: {len(MODELS_TO_DOWNLOAD)}\n")
    
    success_count = 0
    failed_count = 0
    
    for repo_id, info in MODELS_TO_DOWNLOAD.items():
        if download_model(repo_id, info['save_as'], info):
            success_count += 1
        else:
            failed_count += 1
    
    print("\n" + "="*80)
    print(f"DOWNLOAD SUMMARY")
    print("="*80)
    print(f"✓ Successful: {success_count}")
    print(f"✗ Failed/Skipped: {failed_count}")
    
    if success_count > 0:
        print(f"\nNew models saved to: {MODELS_DIR.absolute()}")
        print("\nNext steps:")
        print("1. Update config.py to use new models")
        print("2. Update model_manager.py if new architectures needed")
        print("3. Run test_all_models.py to verify")

if __name__ == "__main__":
    main()
