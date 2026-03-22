"""
Download real medical images from open medical datasets
Using direct download links from research databases
"""
import requests
import os
from pathlib import Path

TEST_DIR = Path("static/test_images/real")
TEST_DIR.mkdir(parents=True, exist_ok=True)

# Real medical images from Kaggle/GitHub/Research datasets (public access)
# These are actual medical images that should work well with trained models
MEDICAL_IMAGES = {
    # Chest X-rays
    "chest_xray_pneumonia.jpg": "https://github.com/ageron/handson-ml2/raw/master/images/classification/chest_xray.png",
    
    # Additional images from open datasets
    # We'll use wget/curl to download from public medical datasets
}

# Alternative: Create script to pull from NIH Chest X-ray dataset
NIH_SAMPLES = [
    "https://openi.nlm.nih.gov/imgs/512/11/11/CXR11_IM-0003-1001.png",
    "https://openi.nlm.nih.gov/imgs/512/11/11/CXR11_IM-0003-2001.png",
]

def download_nih_samples():
    """Download sample X-rays from NIH Open-i"""
    print("Downloading real chest X-rays from NIH Open-i database...")
    
    for i, url in enumerate(NIH_SAMPLES, 1):
        try:
            filename = f"chest_xray_nih_{i}.png"
            filepath = TEST_DIR / filename
            
            if filepath.exists():
                print(f"✓ {filename} already exists")
                continue
            
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"✓ Downloaded {filename} ({len(response.content) / 1024:.1f} KB)")
            else:
                print(f"✗ Failed: HTTP {response.status_code}")
        except Exception as e:
            print(f"✗ Error: {e}")

if __name__ == "__main__":
    download_nih_samples()
    
    # List what we have
    images = list(TEST_DIR.glob("*.jpg")) + list(TEST_DIR.glob("*.jpeg")) + list(TEST_DIR.glob("*.png"))
    print(f"\nTotal real medical images: {len(images)}")
    for img in images:
        size_kb = img.stat().st_size / 1024
        print(f"  - {img.name} ({size_kb:.1f} KB)")
