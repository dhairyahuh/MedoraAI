# Medical Model Weights - Download Links & Requirements

## What We're Using

All models use **PyTorch state_dict** format (.pth files)

### Architecture Summary

| Model Name | Architecture | Classes | Dataset Needed |
|------------|-------------|---------|----------------|
| pneumonia_detector | ResNet-50 | 4 | ChestX-ray/Pneumonia |
| skin_cancer_detector | DenseNet-121 | 7 | ISIC/HAM10000 |
| diabetic_retinopathy_detector | EfficientNet-B0 | 5 | EyePACS/Kaggle DR |
| breast_cancer_detector | MobileNet-V2 | 2 | BreakHis/Mammogram |
| tumor_detector | VGG-19 | 4 | BraTS/Brain MRI |
| lung_nodule_detector | ResNet-34 | 2 | LIDC-IDRI |
| polyp_detector | Inception-v3 | 2 | CVC-ClinicDB |
| heart_disease_detector | ResNet-50 | 4 | Cardiac MRI |
| cancer_grading_detector | DenseNet-121 | 5 | Gleason Grading |
| fracture_detector | Inception-v3 | 2 | MURA |
| kidney_stone_detector | ResNet-34 | 4 | CT Kidney Stone |
| liver_disease_detector | ResNet-50 | 4 | Liver CT |
| retinal_disease_detector | EfficientNet-B0 | 4 | Retinal OCT |
| gi_disease_detector | ResNet-34 | 3 | Kvasir |
| ultrasound_classifier | MobileNet-V2 | 3 | Ultrasound |

---

## Where to Find Pre-Trained Medical Models

### 🟢 Best Public Sources

#### 1. **HuggingFace Hub** (https://huggingface.co/models)
Search for medical imaging models:
- `huggingface.co/models?pipeline_tag=image-classification&other=medical`
- Examples:
  - `nickmuchi/chest-xray-pneumonia-classification`
  - `1aurent/vit_base_patch16_224_diabetic_retinopathy`
  - `Kaludi/Brain-Tumor-Classification-Using-MRI-ResNet50`
  - `mohameddhaoui/breast_cancer_image_classification`

**How to download:**
```bash
# Install huggingface-hub
pip install huggingface-hub

# Download model
from huggingface_hub import hf_hub_download
model_path = hf_hub_download(
    repo_id="nickmuchi/chest-xray-pneumonia-classification",
    filename="pytorch_model.bin"
)
```

#### 2. **TorchHub/Model Zoo** (https://pytorch.org/hub/)
Official PyTorch models - but most are ImageNet only, not medical

#### 3. **Papers with Code** (https://paperswithcode.com/datasets)
- Find papers on medical imaging
- Many include pre-trained weights in GitHub repos
- Search: "medical image classification pretrained"

#### 4. **GitHub Repositories**
Search GitHub for:
- "medical image classification pytorch weights"
- "chest xray pneumonia model.pth"
- "skin cancer detection pretrained"

Example repos:
- `ieee8023/covid-chestxray-dataset` - COVID-19 models
- `arnoweng/CheXNet` - ChestX-ray models
- `MrGiovanni/ModelsGenesis` - Pre-trained medical backbones

#### 5. **Zenodo** (https://zenodo.org)
Academic data repository with some model weights
- Search: "medical imaging model weights"

---

## Specific Model Recommendations

### 1. **Pneumonia Detection (pneumonia_detector.pth)**
**Best option:** ChestX-ray14 trained models
- **CheXNet** (Stanford): https://github.com/arnoweng/CheXNet
  - DenseNet-121 trained on 100K+ chest X-rays
  - Download: `model.pth.tar` from releases
  - Expected accuracy: ~90%

- **COVID-Net**: https://github.com/lindawangg/COVID-Net
  - ResNet variants for pneumonia/COVID
  - Weights in repository

### 2. **Skin Cancer (skin_cancer_detector.pth)**
**Best option:** HAM10000 or ISIC trained models
- **HAM10000 Models**: https://github.com/ptschandl/HAM10000_baseline
  - Multiple architectures available
  - Download trained weights from releases

- **ISIC Challenge Winners**: https://challenge.isic-archive.com
  - Top performer weights sometimes released

### 3. **Diabetic Retinopathy (diabetic_retinopathy_detector.pth)**
**Best option:** Kaggle competition weights
- **Kaggle DR Competition**: https://www.kaggle.com/competitions/diabetic-retinopathy-detection
  - Winner solutions often include weights
  - Search discussions for shared models

- **EyePACS Models**: https://github.com/mikevoets/jama16-retina-replication
  - Replication of published DR detection

### 4. **Brain Tumor (tumor_detector.pth)**
**Best option:** BraTS trained models
- **BraTS Models**: https://github.com/ellisdg/3DUnetCNN
  - Brain tumor segmentation/classification
  - Pre-trained weights available

### 5. **Breast Cancer (breast_cancer_detector.pth)**
**Best option:** BreakHis histopathology
- **BreakHis Models**: https://github.com/taki0112/BreakHis-Tensorflow
  - PyTorch ports available
  - Search for PyTorch conversions

---

## What Files You Need

For each model, place in `models/weights/`:

### File Format
- **Filename**: `<model_name>.pth` (exact match to config.py)
- **Format**: PyTorch state_dict
- **Contents**: Model weights only (not full checkpoint with optimizer)

### Example Structure
```python
# Correct format
torch.save(model.state_dict(), 'pneumonia_detector.pth')

# If download includes full checkpoint:
checkpoint = torch.load('downloaded_model.pth')
model_weights = checkpoint['model_state_dict']  # or checkpoint['state_dict']
torch.save(model_weights, 'pneumonia_detector.pth')
```

### Required Class Counts
Make sure downloaded model has correct number of output classes:

| Model | Required Classes |
|-------|-----------------|
| pneumonia_detector | 4 (Normal, Bacterial, Viral, TB) |
| skin_cancer_detector | 7 (MEL, NV, BCC, AKIEC, BKL, DF, VASC) |
| diabetic_retinopathy_detector | 5 (No DR, Mild, Moderate, Severe, Proliferative) |
| breast_cancer_detector | 2 (Benign, Malignant) |
| tumor_detector | 4 (Glioma, Meningioma, Pituitary, None) |
| Others | See config.py MODEL_SPECS |

---

## Alternative: Train Your Own

If you can't find pre-trained weights, training is actually faster:

### Quick Training Guide

1. **Download Dataset** (2-5 GB each)
   ```bash
   # Example: Pneumonia dataset
   kaggle datasets download -d paultimothymooney/chest-xray-pneumonia
   ```

2. **Train Model** (2-4 hours on RTX 4070)
   ```bash
   python models\train.py --model pneumonia_detector --dataset data\pneumonia --epochs 50
   ```

3. **Weights Auto-Saved**
   - Location: `models/weights/pneumonia_detector.pth`
   - Includes metadata with accuracy

---

## Realistic Expectations

### Public Availability
- ✅ **Pneumonia/ChestX-ray**: Multiple sources, readily available
- ✅ **Skin Cancer/Melanoma**: ISIC models available
- ⚠️ **Diabetic Retinopathy**: Some available, may need Kaggle account
- ⚠️ **Brain Tumor**: Limited, mostly research code
- ❌ **Most others**: Rare, need to train yourself

### Recommended Approach
1. **Start with 2-3 models** that have public weights (pneumonia, skin cancer)
2. **Train your own** for the rest (3-4 hours each)
3. **Use synthetic weights** for demo/testing until trained

---

## Quick Commands

### After you download weights:

```bash
# 1. Place .pth files in models/weights/
# Example: pneumonia_detector.pth, skin_cancer_detector.pth, etc.

# 2. Restart server
python main.py

# 3. Test
python test_pretrained.py

# 4. Check logs
# Should see: "✓ Loaded fine-tuned weights from models\weights\pneumonia_detector.pth"
```

### Converting Other Formats

If you download models in different formats:

```python
# From TensorFlow/Keras
from torchvision import models
import torch

# Load PyTorch model architecture
model = models.resnet50(pretrained=False)
model.fc = torch.nn.Linear(model.fc.in_features, 4)

# Manually convert weights or use ONNX
# Then save: torch.save(model.state_dict(), 'pneumonia_detector.pth')
```

---

## Need Help?

If you find specific model weights and need help converting/integrating:
1. Share the download link
2. I'll help adapt it to our format
3. We'll test and verify accuracy

**Bottom line**: Focus on finding ChestX-ray (pneumonia) and skin cancer models first - these are most common and have best public availability.
