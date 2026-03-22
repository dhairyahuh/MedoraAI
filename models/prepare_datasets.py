"""
Dataset Preparation Utilities
Download and prepare medical imaging datasets for training
"""

import os
import sys
import urllib.request
import zipfile
import tarfile
from pathlib import Path
from typing import Optional
from tqdm import tqdm

sys.path.append(str(Path(__file__).parent.parent))
from config import BASE_DIR


class DownloadProgressBar(tqdm):
    """Progress bar for downloads"""
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


class DatasetDownloader:
    """Download and prepare medical imaging datasets"""
    
    # Public dataset URLs (examples - some may require API keys or manual download)
    DATASETS = {
        "pneumonia": {
            "name": "Chest X-Ray Pneumonia",
            "url": "https://www.kaggle.com/datasets/paultimothymooney/chest-xray-pneumonia/download",
            "size": "~2.3 GB",
            "description": "Chest X-ray images for pneumonia detection (Normal, Pneumonia)",
            "requires_kaggle": True,
            "structure": "chest_xray/{train,val,test}/{NORMAL,PNEUMONIA}/*.jpeg"
        },
        "covid": {
            "name": "COVID-19 Chest X-ray",
            "url": "https://github.com/ieee8023/covid-chestxray-dataset/archive/master.zip",
            "size": "~50 MB",
            "description": "COVID-19 and other lung disease X-rays",
            "requires_kaggle": False,
            "structure": "Manual organization required"
        },
        "melanoma": {
            "name": "ISIC 2019 Melanoma",
            "url": "https://www.kaggle.com/datasets/cdeotte/jpeg-isic2019-384x384/download",
            "size": "~3.5 GB",
            "description": "Skin lesion images for melanoma detection",
            "requires_kaggle": True,
            "structure": "Manual organization by diagnosis"
        },
        "diabetic_retinopathy": {
            "name": "Diabetic Retinopathy Detection",
            "url": "https://www.kaggle.com/c/diabetic-retinopathy-detection/data",
            "size": "~88 GB",
            "description": "Retinal images for diabetic retinopathy grading (0-4)",
            "requires_kaggle": True,
            "structure": "Manual split and organization required"
        },
        "brain_tumor": {
            "name": "Brain Tumor MRI Dataset",
            "url": "https://www.kaggle.com/datasets/masoudnickparvar/brain-tumor-mri-dataset/download",
            "size": "~250 MB",
            "description": "MRI scans for brain tumor classification (4 classes)",
            "requires_kaggle": True,
            "structure": "Training/{glioma,meningioma,notumor,pituitary}/*.jpg"
        },
        "lung_cancer": {
            "name": "Lung Cancer CT Scans",
            "url": "https://www.kaggle.com/datasets/mohamedhanyyy/chest-ctscan-images/download",
            "size": "~750 MB",
            "description": "CT scans for lung cancer detection",
            "requires_kaggle": True,
            "structure": "Manual organization required"
        },
        "tuberculosis": {
            "name": "Tuberculosis Chest X-ray",
            "url": "https://www.kaggle.com/datasets/tawsifurrahman/tuberculosis-tb-chest-xray-dataset/download",
            "size": "~400 MB",
            "description": "Chest X-rays for TB detection (Normal, Tuberculosis)",
            "requires_kaggle": True,
            "structure": "TB_Chest_Radiography_Database/{Normal,Tuberculosis}/*.png"
        }
    }
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize dataset downloader
        
        Args:
            data_dir: Directory to store datasets (default: BASE_DIR/data)
        """
        if data_dir is None:
            data_dir = os.path.join(BASE_DIR, "data")
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Dataset directory: {self.data_dir}")
    
    def list_available_datasets(self):
        """List all available datasets"""
        print("\nAvailable Medical Imaging Datasets:")
        print("=" * 80)
        
        for dataset_id, info in self.DATASETS.items():
            print(f"\n{dataset_id}:")
            print(f"  Name: {info['name']}")
            print(f"  Size: {info['size']}")
            print(f"  Description: {info['description']}")
            print(f"  Kaggle API: {'Required' if info['requires_kaggle'] else 'Not required'}")
            print(f"  Structure: {info['structure']}")
        
        print("\n" + "=" * 80)
    
    def download_from_url(self, url: str, filename: str) -> bool:
        """
        Download file from URL with progress bar
        
        Args:
            url: URL to download from
            filename: Local filename to save to
        
        Returns:
            True if successful, False otherwise
        """
        filepath = self.data_dir / filename
        
        if filepath.exists():
            print(f"✓ {filename} already exists")
            return True
        
        try:
            print(f"Downloading {filename}...")
            with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=filename) as t:
                urllib.request.urlretrieve(url, filepath, reporthook=t.update_to)
            
            print(f"✓ Downloaded {filename}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to download {filename}: {e}")
            if filepath.exists():
                filepath.unlink()
            return False
    
    def extract_archive(self, archive_path: Path, extract_to: Optional[Path] = None) -> bool:
        """
        Extract zip or tar archive
        
        Args:
            archive_path: Path to archive file
            extract_to: Directory to extract to (default: same directory as archive)
        
        Returns:
            True if successful, False otherwise
        """
        if extract_to is None:
            extract_to = archive_path.parent
        
        try:
            print(f"Extracting {archive_path.name}...")
            
            if archive_path.suffix == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
            
            elif archive_path.suffix in ['.tar', '.gz', '.tgz']:
                with tarfile.open(archive_path, 'r:*') as tar_ref:
                    tar_ref.extractall(extract_to)
            
            else:
                print(f"✗ Unsupported archive format: {archive_path.suffix}")
                return False
            
            print(f"✓ Extracted to {extract_to}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to extract {archive_path.name}: {e}")
            return False
    
    def setup_kaggle_api(self):
        """Setup and verify Kaggle API credentials"""
        try:
            import kaggle
            print("✓ Kaggle API is configured")
            return True
        except Exception as e:
            print("\n✗ Kaggle API not configured!")
            print("\nTo download Kaggle datasets:")
            print("1. Create a Kaggle account at https://www.kaggle.com")
            print("2. Go to https://www.kaggle.com/account")
            print("3. Click 'Create New API Token' to download kaggle.json")
            print("4. Place kaggle.json in: C:\\Users\\<username>\\.kaggle\\kaggle.json")
            print("5. Install kaggle: pip install kaggle")
            print(f"\nError: {e}")
            return False
    
    def download_kaggle_dataset(self, dataset_name: str, unzip: bool = True) -> bool:
        """
        Download dataset from Kaggle
        
        Args:
            dataset_name: Kaggle dataset identifier (e.g., 'username/dataset-name')
            unzip: Whether to unzip after downloading
        
        Returns:
            True if successful, False otherwise
        """
        if not self.setup_kaggle_api():
            return False
        
        try:
            import kaggle
            
            print(f"Downloading Kaggle dataset: {dataset_name}")
            kaggle.api.dataset_download_files(
                dataset_name,
                path=str(self.data_dir),
                unzip=unzip
            )
            
            print(f"✓ Downloaded {dataset_name}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to download Kaggle dataset: {e}")
            return False
    
    def prepare_dataset(self, dataset_id: str) -> bool:
        """
        Prepare a specific dataset
        
        Args:
            dataset_id: Dataset identifier from DATASETS dict
        
        Returns:
            True if successful, False otherwise
        """
        if dataset_id not in self.DATASETS:
            print(f"✗ Unknown dataset: {dataset_id}")
            print("Available datasets:", list(self.DATASETS.keys()))
            return False
        
        info = self.DATASETS[dataset_id]
        
        print(f"\n{'='*80}")
        print(f"Preparing: {info['name']}")
        print(f"Size: {info['size']}")
        print(f"Description: {info['description']}")
        print(f"{'='*80}\n")
        
        dataset_dir = self.data_dir / dataset_id
        dataset_dir.mkdir(exist_ok=True)
        
        if info['requires_kaggle']:
            print(f"⚠ This dataset requires Kaggle API")
            print(f"URL: {info['url']}")
            print("\nManual download instructions:")
            print(f"1. Visit {info['url']}")
            print(f"2. Download the dataset")
            print(f"3. Extract to: {dataset_dir}")
            print(f"4. Organize according to: {info['structure']}")
            return False
        
        else:
            # Try direct download for non-Kaggle datasets
            filename = f"{dataset_id}.zip"
            if self.download_from_url(info['url'], filename):
                archive_path = self.data_dir / filename
                if self.extract_archive(archive_path, dataset_dir):
                    print(f"\n✓ Dataset prepared at: {dataset_dir}")
                    return True
        
        return False
    
    def verify_dataset_structure(self, dataset_id: str, dataset_path: Path) -> bool:
        """
        Verify dataset has correct structure for training
        
        Args:
            dataset_id: Dataset identifier
            dataset_path: Path to dataset directory
        
        Returns:
            True if structure is valid, False otherwise
        """
        # Expected structure: dataset_path/{train,val,test}/{class1,class2,...}/*.jpg
        required_splits = ['train', 'val']  # test is optional
        
        for split in required_splits:
            split_dir = dataset_path / split
            if not split_dir.exists():
                print(f"✗ Missing required split: {split}")
                return False
            
            # Check for class directories
            class_dirs = [d for d in split_dir.iterdir() if d.is_dir()]
            if len(class_dirs) == 0:
                print(f"✗ No class directories found in {split}/")
                return False
            
            # Check for images in each class
            for class_dir in class_dirs:
                images = list(class_dir.glob('*'))
                if len(images) == 0:
                    print(f"✗ No images found in {split}/{class_dir.name}/")
                    return False
        
        print(f"✓ Dataset structure is valid")
        return True


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download and prepare medical datasets")
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available datasets'
    )
    parser.add_argument(
        '--dataset',
        type=str,
        help='Download specific dataset',
        choices=list(DatasetDownloader.DATASETS.keys())
    )
    parser.add_argument(
        '--setup-kaggle',
        action='store_true',
        help='Setup and verify Kaggle API'
    )
    
    args = parser.parse_args()
    
    downloader = DatasetDownloader()
    
    if args.list:
        downloader.list_available_datasets()
    
    elif args.setup_kaggle:
        downloader.setup_kaggle_api()
    
    elif args.dataset:
        downloader.prepare_dataset(args.dataset)
    
    else:
        parser.print_help()
        print("\n")
        downloader.list_available_datasets()


if __name__ == "__main__":
    main()
