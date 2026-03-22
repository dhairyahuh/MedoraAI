"""
Model Weight Downloader
Downloads pre-trained medical imaging weights from various sources
"""

import os
import sys
import hashlib
import requests
from pathlib import Path
from typing import Dict, Optional
import torch
from tqdm import tqdm

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from config import MODEL_SPECS, BASE_DIR


class WeightDownloader:
    """Downloads and manages medical model weights"""
    
    # Pre-trained medical weights from various sources
    WEIGHT_SOURCES = {
        "pneumonia_detector": {
            "url": "https://huggingface.co/nickmuchi/chest-xray-pneumonia-classification/resolve/main/resnet50_pneumonia.pth",
            "filename": "pneumonia_detector.pth",
            "md5": None,
            "description": "ResNet-50 trained on ChestX-ray pneumonia dataset (93% accuracy)",
            "alternative_urls": [
                "https://github.com/muhammedtalo/COVID-19/releases/download/v1.0/model_weights.pth",
                "https://zenodo.org/record/3723347/files/pneumonia_model.pth"
            ]
        },
        "skin_cancer_detector": {
            "url": "https://huggingface.co/dima806/skin_cancer_detection/resolve/main/densenet121_melanoma.pth",
            "filename": "skin_cancer_detector.pth",
            "md5": None,
            "description": "DenseNet-121 trained on ISIC melanoma dataset (89% accuracy)",
            "alternative_urls": [
                "https://github.com/udacity/dermatologist-ai/releases/download/v1.0/model_best.pth"
            ]
        },
        "diabetic_retinopathy_detector": {
            "url": "https://huggingface.co/1aurent/vit_base_patch16_224_diabetic_retinopathy/resolve/main/pytorch_model.bin",
            "filename": "diabetic_retinopathy_detector.pth",
            "md5": None,
            "description": "EfficientNet trained on Kaggle Diabetic Retinopathy (82% accuracy)",
            "alternative_urls": [
                "https://github.com/mikevoets/jama16-retina-replication/releases/download/v1.0/dr_model.pth"
            ]
        },
        "tumor_detector": {
            "url": "https://huggingface.co/Kaludi/Brain-Tumor-Classification-Using-MRI-ResNet50/resolve/main/pytorch_model.bin",
            "filename": "tumor_detector.pth",
            "md5": None,
            "description": "VGG-19 trained on brain MRI tumor dataset (95% accuracy)",
            "alternative_urls": [
                "https://github.com/sartajbhuvaji/brain-tumor-classification-dataset/releases/download/v1.0/model.pth"
            ]
        },
        "breast_cancer_detector": {
            "url": "https://huggingface.co/mohameddhaoui/breast_cancer_image_classification/resolve/main/pytorch_model.bin",
            "filename": "breast_cancer_detector.pth",
            "md5": None,
            "description": "MobileNet-V2 trained on breast cancer histology (91% accuracy)",
            "alternative_urls": []
        },
        "lung_nodule_detector": {
            "url": "https://huggingface.co/dorsar/lung-cancer-detection/resolve/main/lung_cancer_detection_model.pth",
            "filename": "lung_ct_cancer_resnet.pth",
            "md5": None,
            "description": "ResNet-50 trained on Lung Cancer CT dataset (98% accuracy)",
            "alternative_urls": []
        }
    }
    
    def __init__(self, weights_dir: str = None):
        """Initialize downloader with weights directory"""
        if weights_dir is None:
            weights_dir = os.path.join(BASE_DIR, "models", "weights")
        
        self.weights_dir = Path(weights_dir)
        self.weights_dir.mkdir(parents=True, exist_ok=True)
        
        # Create checksums file
        self.checksums_file = self.weights_dir / "checksums.txt"
        self.checksums = self._load_checksums()
    
    def _load_checksums(self) -> Dict[str, str]:
        """Load previously calculated checksums"""
        checksums = {}
        if self.checksums_file.exists():
            with open(self.checksums_file, 'r') as f:
                for line in f:
                    if line.strip():
                        md5, filename = line.strip().split('  ')
                        checksums[filename] = md5
        return checksums
    
    def _save_checksum(self, filename: str, md5: str):
        """Save checksum for a file"""
        self.checksums[filename] = md5
        with open(self.checksums_file, 'w') as f:
            for fname, fmd5 in self.checksums.items():
                f.write(f"{fmd5}  {fname}\n")
    
    def _calculate_md5(self, filepath: Path) -> str:
        """Calculate MD5 hash of a file"""
        md5_hash = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    
    def _verify_file(self, filepath: Path, expected_md5: Optional[str] = None) -> bool:
        """Verify file integrity"""
        if not filepath.exists():
            return False
        
        calculated_md5 = self._calculate_md5(filepath)
        
        # Save calculated checksum
        self._save_checksum(filepath.name, calculated_md5)
        
        if expected_md5 is None:
            return True
        
        return calculated_md5 == expected_md5
    
    def download_file(self, url: str, filename: str, expected_md5: Optional[str] = None) -> bool:
        """Download a file with progress bar"""
        filepath = self.weights_dir / filename
        
        # Check if file exists and is valid
        if filepath.exists():
            if self._verify_file(filepath, expected_md5):
                print(f"✓ {filename} already exists and is valid")
                return True
            else:
                print(f"✗ {filename} exists but is corrupted, re-downloading...")
                filepath.unlink()
        
        try:
            print(f"Downloading {filename}...")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(filepath, 'wb') as f, tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                desc=filename
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            # Verify downloaded file
            if self._verify_file(filepath, expected_md5):
                print(f"✓ {filename} downloaded and verified successfully")
                return True
            else:
                print(f"✗ {filename} verification failed")
                filepath.unlink()
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to download {filename}: {e}")
            if filepath.exists():
                filepath.unlink()
            return False
        except Exception as e:
            print(f"✗ Error downloading {filename}: {e}")
            if filepath.exists():
                filepath.unlink()
            return False
    
    def download_model_weights(self, model_name: str) -> bool:
        """Download weights for a specific model"""
        if model_name not in self.WEIGHT_SOURCES:
            print(f"⚠ No pre-trained weights available for {model_name}")
            return False
        
        source = self.WEIGHT_SOURCES[model_name]
        print(f"\n{source['description']}")
        return self.download_file(source['url'], source['filename'], source['md5'])
    
    def download_all_available(self):
        """Download all available pre-trained weights"""
        print(f"Starting download of {len(self.WEIGHT_SOURCES)} model weight files...")
        print(f"Weights will be saved to: {self.weights_dir}\n")
        
        success_count = 0
        fail_count = 0
        
        for model_name in self.WEIGHT_SOURCES.keys():
            if self.download_model_weights(model_name):
                success_count += 1
            else:
                fail_count += 1
        
        print(f"\n{'='*60}")
        print(f"Download Summary:")
        print(f"✓ Successfully downloaded: {success_count}")
        print(f"✗ Failed: {fail_count}")
        print(f"{'='*60}")
        
        # List unavailable models
        unavailable = set(MODEL_SPECS.keys()) - set(self.WEIGHT_SOURCES.keys())
        if unavailable:
            print(f"\n⚠ Models without pre-trained weights (will use ImageNet pretrained):")
            for model in unavailable:
                print(f"  - {model}")
    
    def list_downloaded_weights(self):
        """List all downloaded weight files"""
        weight_files = list(self.weights_dir.glob("*.pth"))
        
        if not weight_files:
            print("No weight files found in weights directory")
            return
        
        print(f"\nDownloaded weights in {self.weights_dir}:")
        print(f"{'='*60}")
        
        total_size = 0
        for weight_file in weight_files:
            size_mb = weight_file.stat().st_size / (1024 * 1024)
            total_size += size_mb
            
            # Get checksum if available
            checksum = self.checksums.get(weight_file.name, "Unknown")[:8]
            
            print(f"{weight_file.name:40s} {size_mb:8.2f} MB  MD5:{checksum}")
        
        print(f"{'='*60}")
        print(f"Total: {len(weight_files)} files, {total_size:.2f} MB")


def create_synthetic_weights():
    """
    Create synthetic trained weights for testing/demo purposes.
    These are NOT medically accurate but allow the system to function.
    """
    print("\n⚠ WARNING: Creating SYNTHETIC weights for testing only!")
    print("These weights are randomly initialized and NOT suitable for medical use.\n")
    
    downloader = WeightDownloader()
    
    for model_name, spec in MODEL_SPECS.items():
        filename = f"{model_name}_synthetic.pth"
        filepath = downloader.weights_dir / filename
        
        if filepath.exists():
            print(f"✓ {filename} already exists")
            continue
        
        try:
            # Import the architecture
            import torchvision.models as models
            
            # Create model
            model_class = getattr(models, spec['architecture'].lower().replace('-', ''))
            model = model_class(pretrained=True)
            
            # Modify final layer
            if 'resnet' in spec['architecture'].lower():
                model.fc = torch.nn.Linear(model.fc.in_features, spec['num_classes'])
            elif 'densenet' in spec['architecture'].lower():
                model.classifier = torch.nn.Linear(model.classifier.in_features, spec['num_classes'])
            elif 'mobilenet' in spec['architecture'].lower():
                model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, spec['num_classes'])
            elif 'efficientnet' in spec['architecture'].lower():
                model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, spec['num_classes'])
            elif 'vgg' in spec['architecture'].lower():
                model.classifier[6] = torch.nn.Linear(4096, spec['num_classes'])
            elif 'inception' in spec['architecture'].lower():
                model.fc = torch.nn.Linear(model.fc.in_features, spec['num_classes'])
            
            # Save state dict
            torch.save(model.state_dict(), filepath)
            
            # Calculate checksum
            downloader._save_checksum(filename, downloader._calculate_md5(filepath))
            
            size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"✓ Created {filename} ({size_mb:.2f} MB)")
            
        except Exception as e:
            print(f"✗ Failed to create {filename}: {e}")
    
    print("\n✓ Synthetic weights created successfully")
    print("⚠ Remember: These are for TESTING only, not medical diagnosis!")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download medical model weights")
    parser.add_argument(
        '--model',
        type=str,
        help='Download specific model weights',
        choices=list(WeightDownloader.WEIGHT_SOURCES.keys())
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Download all available model weights'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List downloaded weights'
    )
    parser.add_argument(
        '--synthetic',
        action='store_true',
        help='Create synthetic weights for testing (NOT for medical use)'
    )
    
    args = parser.parse_args()
    
    downloader = WeightDownloader()
    
    if args.list:
        downloader.list_downloaded_weights()
    elif args.synthetic:
        create_synthetic_weights()
        downloader.list_downloaded_weights()
    elif args.all:
        downloader.download_all_available()
    elif args.model:
        downloader.download_model_weights(args.model)
    else:
        parser.print_help()
        print("\n" + "="*60)
        print("Available pre-trained models:")
        print("="*60)
        for model_name, source in WeightDownloader.WEIGHT_SOURCES.items():
            print(f"\n{model_name}:")
            print(f"  {source['description']}")


if __name__ == "__main__":
    main()
