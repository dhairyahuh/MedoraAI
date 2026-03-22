"""
Download real medical images for testing from various sources
"""
import os
import requests
from pathlib import Path
import json

# Create test images directory
TEST_DIR = Path("static/test_images/real")
TEST_DIR.mkdir(parents=True, exist_ok=True)

# Public medical image datasets (direct download links)
TEST_IMAGES = {
    # Chest X-rays (Pneumonia)
    "pneumonia_positive_1.jpg": "https://raw.githubusercontent.com/ieee8023/covid-chestxray-dataset/master/images/01E392EE-69F9-4E33-BFCE-E5C968654078.jpeg",
    "pneumonia_positive_2.jpg": "https://raw.githubusercontent.com/ieee8023/covid-chestxray-dataset/master/images/auntminnie-2020_01_28_23_51_6665_2020_01_28_Vietnam_coronavirus.jpeg",
    "chest_normal_1.jpg": "https://raw.githubusercontent.com/ieee8023/covid-chestxray-dataset/master/images/1-s2.0-S0929664619305954-gr2_lrg-a.jpg",
    
    # Brain MRI (from sample datasets)
    "brain_tumor_1.jpg": "https://prod-images-static.radiopaedia.org/images/52985885/3f3e3c1e-7a50-4f5a-8c3c-d61f6c0c5a6e_big_gallery.jpeg",
    "brain_normal_1.jpg": "https://prod-images-static.radiopaedia.org/images/52985886/5f5e3c1e-7a50-4f5a-8c3c-d61f6c0c5a6f_big_gallery.jpeg",
    
    # Skin lesions (from ISIC archive - public samples)
    "skin_melanoma_1.jpg": "https://isic-challenge-data.s3.amazonaws.com/2020/ISIC_0000000.jpg",
    "skin_benign_1.jpg": "https://isic-challenge-data.s3.amazonaws.com/2020/ISIC_0000001.jpg",
    
    # Diabetic Retinopathy (from public samples)
    "retina_dr_1.jpg": "https://raw.githubusercontent.com/naina725/Diabetic-Retinopathy-Detection/master/sample_images/10_left.jpeg",
    "retina_normal_1.jpg": "https://raw.githubusercontent.com/naina725/Diabetic-Retinopathy-Detection/master/sample_images/19_left.jpeg",
}

# Alternative: Use placeholder images that look medical
FALLBACK_IMAGES = {
    "test_xray_1.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Chest_radiograph_in_influenza_and_Haemophilus_influenzae%2C_posteroanterior%2C_annotated.jpg/800px-Chest_radiograph_in_influenza_and_Haemophilus_influenzae%2C_posteroanterior%2C_annotated.jpg",
    "test_mri_1.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/MRT_Kopf_nativ_Sag_T1.jpg/800px-MRT_Kopf_nativ_Sag_T1.jpg",
    "test_ct_1.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/CT_of_human_chest_with_lungs_and_ribs.png/800px-CT_of_human_chest_with_lungs_and_ribs.png",
    "test_skin_1.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Melanoma.jpg/800px-Melanoma.jpg",
    "test_mammogram_1.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cb/Mammo_breast_cancer.jpg/800px-Mammo_breast_cancer.jpg",
    "test_retina_1.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Fundus_photograph_of_normal_left_eye.jpg/800px-Fundus_photograph_of_normal_left_eye.jpg",
}

def download_image(url, filename):
    """Download image from URL"""
    filepath = TEST_DIR / filename
    if filepath.exists():
        print(f"✓ {filename} already exists")
        return True
    
    try:
        response = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"✓ Downloaded {filename} ({len(response.content) / 1024:.1f} KB)")
            return True
        else:
            print(f"✗ Failed to download {filename} (HTTP {response.status_code})")
            return False
    except Exception as e:
        print(f"✗ Error downloading {filename}: {e}")
        return False

def main():
    print("=" * 60)
    print("DOWNLOADING REAL MEDICAL TEST IMAGES")
    print("=" * 60)
    
    # Try primary sources
    print("\n1. Downloading from primary medical datasets...")
    success_count = 0
    for filename, url in TEST_IMAGES.items():
        if download_image(url, filename):
            success_count += 1
    
    # Try fallback (Wikipedia medical images)
    print("\n2. Downloading from fallback sources (Wikipedia)...")
    for filename, url in FALLBACK_IMAGES.items():
        if download_image(url, filename):
            success_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"DOWNLOAD COMPLETE: {success_count}/{len(TEST_IMAGES) + len(FALLBACK_IMAGES)} images")
    print(f"Images saved to: {TEST_DIR.absolute()}")
    print("=" * 60)
    
    # List downloaded files
    downloaded = list(TEST_DIR.glob("*.jpg")) + list(TEST_DIR.glob("*.jpeg")) + list(TEST_DIR.glob("*.png"))
    if downloaded:
        print(f"\n✓ {len(downloaded)} images ready for testing:")
        for img in sorted(downloaded):
            size_kb = img.stat().st_size / 1024
            print(f"  - {img.name} ({size_kb:.1f} KB)")
    else:
        print("\n⚠ No images downloaded. Will use synthetic test images.")

if __name__ == "__main__":
    main()
