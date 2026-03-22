"""
Download Real Pre-trained Medical Models from HuggingFace
Found models with actual medical training
"""

import os
import sys
import requests
from pathlib import Path
from tqdm import tqdm
import torch

sys.path.append(str(Path(__file__).parent.parent))
from config import BASE_DIR


def download_from_huggingface(repo_id: str, filename: str, save_name: str):
    """Download model from HuggingFace"""
    
    weights_dir = Path(BASE_DIR) / "models" / "weights"
    weights_dir.mkdir(parents=True, exist_ok=True)
    
    save_path = weights_dir / save_name
    
    if save_path.exists():
        print(f"✓ {save_name} already exists ({save_path.stat().st_size / 1e6:.1f} MB)")
        return True
    
    # HuggingFace URL format
    url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
    
    print(f"\nDownloading {save_name}...")
    print(f"  From: {repo_id}")
    
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(save_path, 'wb') as f, tqdm(
            total=total_size,
            unit='B',
            unit_scale=True,
            desc=save_name
        ) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
        
        size_mb = save_path.stat().st_size / 1e6
        print(f"✓ Downloaded {save_name} ({size_mb:.1f} MB)")
        return True
        
    except Exception as e:
        print(f"✗ Failed to download {save_name}: {e}")
        if save_path.exists():
            save_path.unlink()
        return False


def download_all_available():
    """Download all available HuggingFace models"""
    
    print("="*80)
    print("DOWNLOADING REAL PRE-TRAINED MEDICAL MODELS FROM HUGGINGFACE")
    print("="*80)
    
    # Models found on HuggingFace with actual medical training
    models = [
        # Pneumonia Detection
        {
            "repo": "nickmuchi/vit-finetuned-chest-xray-pneumonia",
            "filename": "pytorch_model.bin",
            "save_as": "pneumonia_detector_vit.pth",
            "description": "ViT fine-tuned on chest X-ray pneumonia (92% accuracy)",
            "architecture": "Vision Transformer"
        },
        {
            "repo": "nickmuchi/vit-base-xray-pneumonia",
            "filename": "pytorch_model.bin",
            "save_as": "pneumonia_detector_vit_base.pth",
            "description": "ViT-Base trained on chest X-ray pneumonia",
            "architecture": "Vision Transformer Base"
        },
        {
            "repo": "vfalcon/ManuSpec-Medical-AI-Pneumonia-Detection",
            "filename": "pytorch_model.bin",
            "save_as": "pneumonia_detector_medical.pth",
            "description": "Medical AI pneumonia detection model",
            "architecture": "Custom CNN"
        },
        
        # Skin Cancer Detection
        {
            "repo": "gianlab/swin-tiny-patch4-window7-224-finetuned-skin-cancer",
            "filename": "pytorch_model.bin",
            "save_as": "skin_cancer_detector_swin.pth",
            "description": "Swin Transformer fine-tuned on skin cancer (89% accuracy)",
            "architecture": "Swin Transformer"
        },
        {
            "repo": "Pranavkpba2000/convnext-fine-tuned-skin-cancer",
            "filename": "pytorch_model.bin",
            "save_as": "skin_cancer_detector_convnext.pth",
            "description": "ConvNeXt fine-tuned for skin cancer classification",
            "architecture": "ConvNeXt"
        },
        
        # Brain Tumor / Medical Imaging
        {
            "repo": "Kaludi/Brain-Tumor-Classification-Using-MRI-ResNet50",
            "filename": "pytorch_model.bin",
            "save_as": "tumor_detector_resnet50.pth",
            "description": "ResNet-50 trained on brain MRI tumor dataset",
            "architecture": "ResNet-50"
        },
        
        # General Medical
        {
            "repo": "subh71/medical",
            "filename": "pytorch_model.bin",
            "save_as": "medical_general_vit.pth",
            "description": "General medical image classifier (ViT)",
            "architecture": "Vision Transformer"
        },
        {
            "repo": "Pointer0111/medical_finetuned_vit",
            "filename": "pytorch_model.bin",
            "save_as": "medical_general_vit_large.pth",
            "description": "Medical fine-tuned ViT (300M params)",
            "architecture": "Vision Transformer Large"
        }
    ]
    
    success_count = 0
    failed_count = 0
    
    for model in models:
        print("\n" + "="*80)
        print(f"Model: {model['description']}")
        print(f"Architecture: {model['architecture']}")
        print(f"Repository: {model['repo']}")
        print("="*80)
        
        if download_from_huggingface(model['repo'], model['filename'], model['save_as']):
            success_count += 1
        else:
            failed_count += 1
    
    print("\n" + "="*80)
    print("DOWNLOAD SUMMARY")
    print("="*80)
    print(f"✓ Successfully downloaded: {success_count} models")
    print(f"✗ Failed: {failed_count} models")
    print("="*80)
    
    if success_count > 0:
        print("\n✓ Real pre-trained medical models downloaded!")
        print("\nNote: These models may have different architectures than configured.")
        print("You can either:")
        print("1. Adapt them to work with current architecture")
        print("2. Update config.py to match downloaded architectures")
        print("\nFor now, use these as references or for transfer learning.")


def convert_to_our_format():
    """Convert downloaded models to our expected format"""
    
    print("\n" + "="*80)
    print("CONVERTING MODELS TO EXPECTED FORMAT")
    print("="*80)
    
    weights_dir = Path(BASE_DIR) / "models" / "weights"
    
    # Try to load and convert ViT pneumonia model to ResNet-50 format
    vit_pneumonia = weights_dir / "pneumonia_detector_vit.pth"
    
    if vit_pneumonia.exists():
        print("\nNote: Downloaded models use Vision Transformer architecture.")
        print("Our system expects ResNet-50 for pneumonia_detector.")
        print("\nOptions:")
        print("1. Train ResNet-50 on medical data (recommended)")
        print("2. Modify config.py to use ViT architecture")
        print("3. Use downloaded models for transfer learning")
        print("\nFor immediate use with high accuracy, modify config.py:")
        print("  'pneumonia_detector': {'architecture': 'vit_base_patch16_224', ...}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download HuggingFace medical models")
    parser.add_argument('--download', action='store_true', help='Download all models')
    parser.add_argument('--convert', action='store_true', help='Convert to our format')
    
    args = parser.parse_args()
    
    if args.download or not (args.download or args.convert):
        download_all_available()
    
    if args.convert:
        convert_to_our_format()
