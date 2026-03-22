"""
Find and download 4 additional real medical models from HuggingFace
Target: 10 working models with real medical training

Currently have 6:
1. pneumonia_detector (chest X-ray) - dima806/chest_xray
2. skin_cancer_detector (dermoscopy) - existing
3. tumor_detector (brain MRI) - andrei-teodor/vit-base-brain-mri
4. diabetic_retinopathy_detector - AsmaaElnagger
5. breast_cancer_detector - Falah/vit-base-breast-cancer
6. lung_nodule_detector - DunnBC22/lung_and_colon_cancer
7. polyp_detector (repurposed to COVID CT) - DunnBC22/covid_19_ct_scans
8. fracture_detector - prithivMLmods/Bone-Fracture

Need 4 more from remaining models:
- heart_disease_detector
- cancer_grading_detector (histopathology)
- kidney_stone_detector
- retinal_disease_detector
- gi_disease_detector
- liver_disease_detector
- ultrasound_detector
"""
import os
from pathlib import Path
from huggingface_hub import hf_hub_download
import torch
from safetensors.torch import load_file
from tqdm import tqdm

WEIGHTS_DIR = Path("models/weights")
WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

# 4 additional models to download for 10 total
MODELS_TO_DOWNLOAD = [
    {
        "repo": "Devarshi/Brain_Tumor_Classification",
        "description": "Brain Tumor Classification (Swin Transformer)",
        "output_file": "tumor_detector_swin.pth",
        "architecture": "swin_tiny_patch4_window7_224"
    },
    {
        "repo": "sergiopaniego/fine_tuning_vit_custom_dataset_breastcancer-ultrasound-images",
        "description": "Breast Cancer Ultrasound (ViT)",
        "output_file": "ultrasound_detector_vit.pth",
        "architecture": "vit_base_patch16_224"
    },
    {
        "repo": "oohtmeel/swin-tiny-patch4-finetuned-lung-cancer-ct-scans",
        "description": "Lung Cancer CT Scans (Swin Transformer)",
        "output_file": "lung_ct_swin.pth",
        "architecture": "swin_tiny_patch4_window7_224"
    },
    {
        "repo": "1aurent/vit_small_patch16_224.kaiko_ai_towards_large_pathology_fms",
        "description": "Pathology/Cancer Grading (ViT Small)",
        "output_file": "cancer_grading_vit.pth",
        "architecture": "vit_small_patch16_224"
    }
]

def download_model(repo_id, output_filename, description):
    """Download model from HuggingFace Hub"""
    output_path = WEIGHTS_DIR / output_filename
    
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"✓ {output_filename} already exists ({size_mb:.1f} MB)")
        return True
    
    print(f"\n{'='*60}")
    print(f"Downloading: {description}")
    print(f"Repository: {repo_id}")
    print(f"Output: {output_filename}")
    print(f"{'='*60}")
    
    try:
        # Try to download model.safetensors first
        print("Attempting to download model.safetensors...")
        try:
            file_path = hf_hub_download(
                repo_id=repo_id,
                filename="model.safetensors",
                cache_dir=".cache"
            )
            print(f"✓ Downloaded model.safetensors")
            
            # Load and convert to PyTorch
            state_dict = load_file(file_path)
            torch.save(state_dict, output_path)
            
        except Exception as e1:
            print(f"model.safetensors not found, trying pytorch_model.bin...")
            try:
                file_path = hf_hub_download(
                    repo_id=repo_id,
                    filename="pytorch_model.bin",
                    cache_dir=".cache"
                )
                print(f"✓ Downloaded pytorch_model.bin")
                
                # Load and save
                state_dict = torch.load(file_path, map_location='cpu')
                torch.save(state_dict, output_path)
                
            except Exception as e2:
                print(f"✗ Both model files failed:")
                print(f"  - model.safetensors: {e1}")
                print(f"  - pytorch_model.bin: {e2}")
                return False
        
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"✓ Saved to {output_filename} ({size_mb:.1f} MB)")
        return True
        
    except Exception as e:
        print(f"✗ Failed to download {repo_id}: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("DOWNLOADING 4 ADDITIONAL MEDICAL MODELS")
    print("Target: 10 working models with real medical training")
    print("="*60)
    
    success = []
    failed = []
    
    for model_info in MODELS_TO_DOWNLOAD:
        if download_model(model_info["repo"], model_info["output_file"], model_info["description"]):
            success.append(model_info)
        else:
            failed.append(model_info)
    
    # Summary
    print("\n" + "="*60)
    print(f"DOWNLOAD SUMMARY")
    print("="*60)
    print(f"✓ Successful: {len(success)}/{len(MODELS_TO_DOWNLOAD)}")
    print(f"✗ Failed: {len(failed)}/{len(MODELS_TO_DOWNLOAD)}")
    
    if success:
        print(f"\n✓ Successfully downloaded models:")
        total_size = 0
        for model in success:
            filepath = WEIGHTS_DIR / model["output_file"]
            if filepath.exists():
                size_mb = filepath.stat().st_size / (1024 * 1024)
                total_size += size_mb
                print(f"  - {model['output_file']} ({size_mb:.1f} MB)")
                print(f"    {model['description']}")
                print(f"    Architecture: {model['architecture']}")
        print(f"\nTotal size: {total_size:.1f} MB")
    
    if failed:
        print(f"\n✗ Failed models:")
        for model in failed:
            print(f"  - {model['description']} ({model['repo']})")
    
    # Next steps
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    if success:
        print("1. Update config.py to configure these 4 new models")
        print("2. Update model_manager.py if new architectures needed")
        print("3. Test all 10 models with real medical images")
        print("\nModel mappings for config.py:")
        for model in success:
            if "ultrasound" in model["output_file"]:
                print(f"  - ultrasound_detector: {model['architecture']}, weight_file='{model['output_file']}'")
            elif "tumor_detector_swin" in model["output_file"]:
                print(f"  - tumor_detector (alternative): {model['architecture']}, weight_file='{model['output_file']}'")
            elif "lung_ct" in model["output_file"]:
                print(f"  - cancer_grading_detector: {model['architecture']}, weight_file='{model['output_file']}'")
            elif "cancer_grading" in model["output_file"]:
                print(f"  - gi_disease_detector: {model['architecture']}, weight_file='{model['output_file']}'")

if __name__ == "__main__":
    main()
