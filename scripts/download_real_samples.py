"""
Download real medical image samples from public datasets for testing
"""
import requests
from pathlib import Path
from tqdm import tqdm
import time

# Create test images directory
SAMPLE_DIR = Path("static/test_images/real_samples")
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

# Public medical image URLs from open datasets - COMPREHENSIVE SET FOR ALL 10 MODELS
SAMPLE_IMAGES = {
    # 1. Chest X-rays (Pneumonia detection)
    'chest_xray_pneumonia_1.jpeg': 'https://raw.githubusercontent.com/ieee8023/covid-chestxray-dataset/master/images/01E392EE-69F9-4E33-BFCE-E5C968654078.jpeg',
    'chest_xray_pneumonia_2.jpeg': 'https://raw.githubusercontent.com/ieee8023/covid-chestxray-dataset/master/images/nejmc2001573_f1a.jpeg',
    'chest_xray_normal.jpeg': 'https://raw.githubusercontent.com/ieee8023/covid-chestxray-dataset/master/images/1-s2.0-S0929664620300449-gr2_lrg-d.jpg',
    
    # 2. COVID-19 CT Scans
    'covid_ct_1.jpg': 'https://raw.githubusercontent.com/ieee8023/covid-chestxray-dataset/master/images/covid-19-pneumonia-7-PA.jpg',
    'covid_ct_2.jpg': 'https://raw.githubusercontent.com/ieee8023/covid-chestxray-dataset/master/images/covid-19-pneumonia-14-L-0.jpg',
    
    # 3. Brain MRI (Tumor detection)
    'brain_tumor_glioma.jpg': 'https://raw.githubusercontent.com/sartajbhuvaji/brain-tumor-classification-dataset/master/Training/glioma_tumor/image(1).jpg',
    'brain_tumor_meningioma.jpg': 'https://raw.githubusercontent.com/sartajbhuvaji/brain-tumor-classification-dataset/master/Training/meningioma_tumor/image(1).jpg',
    'brain_tumor_pituitary.jpg': 'https://raw.githubusercontent.com/sartajbhuvaji/brain-tumor-classification-dataset/master/Training/pituitary_tumor/image(1).jpg',
    
    # 4. Skin lesions (Dermoscopy)
    'skin_melanoma.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/24/Melanoma.jpg/800px-Melanoma.jpg',
    'skin_basal_cell.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/Basalcellcarcinoma2.jpg/800px-Basalcellcarcinoma2.jpg',
    'skin_keratosis.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Seborrheic_keratosis.jpg/800px-Seborrheic_keratosis.jpg',
    
    # 5. Diabetic Retinopathy (Fundus)
    'retina_dr_severe.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Fundus_photograph_of_diabetic_retinopathy.jpg/800px-Fundus_photograph_of_diabetic_retinopathy.jpg',
    'retina_dr_laser.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Fundus_photo_showing_scatter_laser_surgery_for_diabetic_retinopathy_EDA09.JPG/800px-Fundus_photo_showing_scatter_laser_surgery_for_diabetic_retinopathy_EDA09.JPG',
    'retina_normal.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Fundus_photograph_of_normal_left_eye.jpg/800px-Fundus_photograph_of_normal_left_eye.jpg',
    
    # 6. Breast Cancer (Mammogram & Histopathology)
    'breast_mammogram.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/cb/Mammo_breast_cancer.jpg/800px-Mammo_breast_cancer.jpg',
    'breast_histo_idc.jpg': 'https://raw.githubusercontent.com/basveeling/pcam/master/pcam.jpg',
    
    # 7. Lung/Colon Cancer (Histopathology)
    'lung_adenocarcinoma.jpeg': 'https://raw.githubusercontent.com/tampapath/lung_colon_image_set/master/lung_image_sets/lung_aca/lungaca1.jpeg',
    'lung_squamous.jpeg': 'https://raw.githubusercontent.com/tampapath/lung_colon_image_set/master/lung_image_sets/lung_scc/lungscc1.jpeg',
    'colon_adenocarcinoma.jpeg': 'https://raw.githubusercontent.com/tampapath/lung_colon_image_set/master/colon_image_sets/colon_aca/colonca1.jpeg',
    
    # 8. Bone Fractures (X-ray)
    'fracture_wrist.png': 'https://raw.githubusercontent.com/Jhilbertxtu/BoneAge/master/data/train/1377.png',
    'fracture_hand.png': 'https://raw.githubusercontent.com/Jhilbertxtu/BoneAge/master/data/train/1388.png',
    'fracture_elbow.png': 'https://raw.githubusercontent.com/Jhilbertxtu/BoneAge/master/data/train/1399.png',
    
    # 9. Lung CT (Cancer grading)
    'lung_ct_cancer.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/CT_of_human_chest_with_lungs_and_ribs.png/800px-CT_of_human_chest_with_lungs_and_ribs.png',
    
    # 10. Breast Ultrasound
    'breast_ultrasound_mass.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/51/Medical_ultrasound_434.jpg/800px-Medical_ultrasound_434.jpg',
}

def download_file(url, filename):
    """Download a file with progress bar"""
    try:
        print(f"Downloading {filename}...")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        filepath = SAMPLE_DIR / filename
        
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
        
        print(f"✓ Saved: {filepath}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to download {filename}: {e}")
        return False

def main():
    print("="*80)
    print("DOWNLOADING REAL MEDICAL IMAGE SAMPLES")
    print("="*80)
    print(f"\nDestination: {SAMPLE_DIR.absolute()}\n")
    
    success_count = 0
    failed_count = 0
    
    for filename, url in SAMPLE_IMAGES.items():
        if download_file(url, filename):
            success_count += 1
        else:
            failed_count += 1
        time.sleep(0.5)  # Be nice to servers
    
    print("\n" + "="*80)
    print(f"Download complete: {success_count} succeeded, {failed_count} failed")
    print("="*80)
    
    if success_count > 0:
        print(f"\n✓ Real medical images saved to: {SAMPLE_DIR.absolute()}")
        print("\nYou can now test with real images using:")
        print("  python test_real_images.py")

if __name__ == "__main__":
    main()
