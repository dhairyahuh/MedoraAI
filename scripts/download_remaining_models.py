#!/usr/bin/env python3
"""
Download remaining 4 models from HuggingFace
- polyp_detector (COVID-19 CT scans)
- cancer_grading_detector (Lung CT Swin)
- fracture_detector (Bone Fracture SigLIP)
- ultrasound_classifier (Breast Ultrasound)
"""
import os
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Set base directory
BASE_DIR = Path(__file__).parent.parent
WEIGHTS_DIR = BASE_DIR / "models" / "weights"
WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("DOWNLOADING REMAINING 4 HUGGINGFACE MODELS")
print("=" * 70)

# Models to download with their HuggingFace sources
MODELS_TO_DOWNLOAD = {
    # 1. COVID-19 CT Scan Detection (polyp_detector)
    "covid_ct": {
        "hf_model": "DunnBC22/vit-base-patch16-224-in21k_covid_19_ct_scans",
        "local_dir": "covid_ct",
        "weight_file": "covid_ct_vit.pth",
        "description": "COVID-19 CT Scan Detection (ViT)",
        "classes": ["COVID-19", "Normal"]
    },
    
    # 2. Lung Cancer CT Grading (cancer_grading_detector)
    "lung_ct_swin": {
        "hf_model": "oohtmeel/swin-tiny-patch4-finetuned-lung-cancer-ct-scans",
        "local_dir": "lung_ct_swin",
        "weight_file": "lung_ct_swin.pth",
        "description": "Lung Cancer CT Grading (Swin Transformer)",
        "classes": ["Large Cell Carcinoma", "Normal", "Squamous Cell Carcinoma"]
    },
    
    # 3. Bone Fracture Detection (fracture_detector)
    "bone_fracture": {
        "hf_model": "prithivMLmods/Bone-Fracture-Detection",
        "local_dir": "bone_fracture",
        "weight_file": "bone_fracture_siglip.pth",
        "description": "Bone Fracture Detection (SigLIP)",
        "classes": ["Elbow Positive", "Finger Positive", "Hand Positive", "Shoulder Positive", "Wrist Positive", "Negative"]
    },
    
    # 4. Breast Ultrasound Classification (ultrasound_classifier)
    "ultrasound": {
        "hf_model": "sergiopaniego/fine_tuning_vit_custom_dataset_breastcancer-ultrasound-images",
        "local_dir": "ultrasound",
        "weight_file": "ultrasound_detector_vit.pth",
        "description": "Breast Ultrasound Classification (ViT)",
        "classes": ["Benign", "Malignant", "Normal"]
    }
}

def download_model(model_key, model_info):
    """Download a single model from HuggingFace"""
    from transformers import AutoModelForImageClassification, AutoImageProcessor
    
    hf_model = model_info["hf_model"]
    local_dir = WEIGHTS_DIR / model_info["local_dir"]
    description = model_info["description"]
    
    print(f"\n{'='*60}")
    print(f"Downloading: {description}")
    print(f"From: {hf_model}")
    print(f"To: {local_dir}")
    print("="*60)
    
    try:
        # Create local directory
        local_dir.mkdir(parents=True, exist_ok=True)
        
        # Download model
        print("  [1/2] Downloading model...")
        model = AutoModelForImageClassification.from_pretrained(
            hf_model,
            trust_remote_code=True
        )
        
        # Download processor
        print("  [2/2] Downloading image processor...")
        try:
            processor = AutoImageProcessor.from_pretrained(
                hf_model,
                trust_remote_code=True
            )
        except Exception as e:
            logger.warning(f"Could not download processor: {e}")
            processor = None
        
        # Save locally
        print(f"  Saving to {local_dir}...")
        model.save_pretrained(str(local_dir))
        if processor:
            processor.save_pretrained(str(local_dir))
        
        # Get class labels
        if hasattr(model.config, 'id2label'):
            classes = list(model.config.id2label.values())
            print(f"  Classes: {classes}")
        else:
            classes = model_info.get("classes", [])
            print(f"  Classes (from config): {classes}")
        
        print(f"  ✓ Successfully downloaded {description}")
        return True, classes
        
    except Exception as e:
        logger.error(f"  ✗ Failed to download {description}: {e}")
        return False, []

def main():
    results = {}
    
    for model_key, model_info in MODELS_TO_DOWNLOAD.items():
        success, classes = download_model(model_key, model_info)
        results[model_key] = {
            "success": success,
            "classes": classes,
            "description": model_info["description"]
        }
    
    # Print summary
    print("\n" + "="*70)
    print("DOWNLOAD SUMMARY")
    print("="*70)
    
    for model_key, result in results.items():
        status = "✓" if result["success"] else "✗"
        print(f"{status} {result['description']}")
        if result["classes"]:
            print(f"    Classes: {result['classes']}")
    
    # Count successes
    successes = sum(1 for r in results.values() if r["success"])
    print(f"\n{successes}/{len(results)} models downloaded successfully")
    
    if successes < len(results):
        print("\nFailed downloads may need manual intervention.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
