# Production Model Training & Deployment Guide

## Overview

This guide explains how to train medical imaging models with real datasets and deploy them with production-ready weights.

## Quick Start: Create Synthetic Weights (Testing Only)

For testing purposes, you can create synthetic weights:

```bash
# Activate virtual environment
.\.venv\Scripts\activate

# Create synthetic weights for all models
python models\download_weights.py --synthetic
```

⚠️ **WARNING**: Synthetic weights are randomly initialized and NOT suitable for medical diagnosis!

---

## Production Setup: Train Real Medical Models

### Step 1: Prepare Your Environment

```bash
# Activate virtual environment
.\.venv\Scripts\activate

# Install additional training dependencies
pip install kaggle tqdm
```

### Step 2: Setup Kaggle API (Required for Most Datasets)

Most medical imaging datasets are hosted on Kaggle. Setup instructions:

1. Create a Kaggle account at https://www.kaggle.com
2. Go to https://www.kaggle.com/account
3. Click **"Create New API Token"** to download `kaggle.json`
4. Place `kaggle.json` in: `C:\Users\<username>\.kaggle\kaggle.json`

Verify setup:
```bash
python models\prepare_datasets.py --setup-kaggle
```

### Step 3: Download Medical Datasets

List available datasets:
```bash
python models\prepare_datasets.py --list
```

**Available Datasets:**

| Dataset ID | Name | Size | Description |
|------------|------|------|-------------|
| `pneumonia` | Chest X-Ray Pneumonia | ~2.3 GB | Normal vs Pneumonia classification |
| `covid` | COVID-19 Chest X-ray | ~50 MB | COVID-19 and lung diseases |
| `melanoma` | ISIC 2019 Melanoma | ~3.5 GB | Skin lesion classification |
| `diabetic_retinopathy` | Diabetic Retinopathy | ~88 GB | Retinopathy grading (0-4) |
| `brain_tumor` | Brain Tumor MRI | ~250 MB | 4-class brain tumor classification |
| `lung_cancer` | Lung Cancer CT | ~750 MB | Lung cancer detection |
| `tuberculosis` | TB Chest X-ray | ~400 MB | TB vs Normal classification |

**Manual Download (Kaggle datasets):**

1. Visit the Kaggle dataset page
2. Download and extract to: `medical-inference-server/data/<dataset_id>/`
3. Organize into training structure:

```
data/
  <dataset_id>/
    train/
      class1/
        image1.jpg
        image2.jpg
      class2/
        image1.jpg
    val/
      class1/
        image1.jpg
      class2/
        image1.jpg
    test/  (optional)
      class1/
        image1.jpg
```

### Step 4: Train Models

Train a specific model:

```bash
python models\train.py --model pneumonia_detector --dataset data\pneumonia --epochs 50
```

**Training Parameters:**

- `--model`: Model name from config.py (required)
- `--dataset`: Path to dataset directory (required)
- `--epochs`: Number of training epochs (default: 50)
- `--batch-size`: Batch size (default: 32)
- `--lr`: Learning rate (default: 0.001)

**Example Training Commands:**

```bash
# Train pneumonia detector
python models\train.py --model pneumonia_detector --dataset data\pneumonia --epochs 50 --batch-size 32

# Train melanoma detector with custom learning rate
python models\train.py --model melanoma_detector --dataset data\melanoma --epochs 100 --lr 0.0001

# Train brain tumor classifier
python models\train.py --model brain_tumor_classifier --dataset data\brain_tumor --epochs 75
```

**Training Output:**

- Trained weights saved to: `models/weights/<model_name>.pth`
- Metadata saved to: `models/weights/<model_name>_metadata.json`
- Training history included in checkpoint

### Step 5: Download Pre-trained Weights (Alternative)

If available, download pre-trained weights instead of training:

```bash
# List available pre-trained weights
python models\download_weights.py --list

# Download all available weights
python models\download_weights.py --all

# Download specific model
python models\download_weights.py --model pneumonia_detector
```

**Note**: Pre-trained weights URLs are examples. Most medical models require training on your specific data.

### Step 6: Verify Model Weights

Check downloaded/trained weights:

```bash
python models\download_weights.py --list
```

Example output:
```
Downloaded weights in models\weights:
============================================================
pneumonia_detector.pth                     98.45 MB  MD5:a1b2c3d4
melanoma_detector.pth                     112.32 MB  MD5:e5f6g7h8
brain_tumor_classifier.pth                 87.21 MB  MD5:i9j0k1l2
============================================================
Total: 3 files, 297.98 MB
```

---

## Model Specifications

### All 15 Models Configured:

1. **pneumonia_detector** (ResNet-50)
   - Classes: Normal, Bacterial Pneumonia, Viral Pneumonia
   - Input: 224x224 chest X-rays
   - Dataset: ChestX-ray14

2. **covid_classifier** (ResNet-34)
   - Classes: Normal, COVID-19, Pneumonia
   - Input: 224x224 chest X-rays
   - Dataset: COVID-19 Radiography

3. **melanoma_detector** (DenseNet-121)
   - Classes: Melanoma, Nevus, Seborrheic Keratosis, BCC, etc.
   - Input: 224x224 skin lesion images
   - Dataset: ISIC 2019

4. **diabetic_retinopathy** (MobileNet-V2)
   - Classes: No DR, Mild, Moderate, Severe, Proliferative DR
   - Input: 224x224 retinal fundus images
   - Dataset: Kaggle Diabetic Retinopathy

5. **brain_tumor_classifier** (EfficientNet-B0)
   - Classes: Glioma, Meningioma, No Tumor, Pituitary
   - Input: 224x224 brain MRI scans
   - Dataset: Brain Tumor MRI

6. **lung_cancer_detector** (VGG-19)
   - Classes: Normal, Adenocarcinoma, Large Cell, Squamous Cell
   - Input: 224x224 lung CT scans

7. **tb_detector** (Inception-v3)
   - Classes: Normal, Tuberculosis
   - Input: 299x299 chest X-rays
   - Dataset: TBX11K

8. **breast_cancer_detector** (ResNet-50)
   - Classes: Benign, Malignant
   - Input: 224x224 mammogram images

9. **alzheimer_classifier** (DenseNet-121)
   - Classes: Mild Demented, Moderate, Non-Demented, Very Mild
   - Input: 224x224 brain MRI

10. **kidney_stone_detector** (MobileNet-V2)
    - Classes: Normal, Stone, Cyst, Tumor
    - Input: 224x224 CT scans

11. **bone_fracture_detector** (EfficientNet-B0)
    - Classes: Fractured, Not Fractured
    - Input: 224x224 X-rays

12. **skin_disease_classifier** (VGG-19)
    - Classes: Acne, Eczema, Melanoma, Psoriasis, etc.
    - Input: 224x224 skin images

13. **glaucoma_detector** (Inception-v3)
    - Classes: Normal, Glaucoma
    - Input: 299x299 retinal images

14. **heart_disease_classifier** (ResNet-34)
    - Classes: Normal, CAD, MI, Cardiomyopathy
    - Input: 224x224 cardiac MRI

15. **liver_disease_detector** (DenseNet-121)
    - Classes: Normal, Cirrhosis, Hepatitis, Tumor
    - Input: 224x224 liver CT scans

---

## Weight File Management

### Weight File Structure

```
models/
  weights/
    <model_name>.pth          # PyTorch state dict
    <model_name>_metadata.json # Training metadata
    checksums.txt              # MD5 checksums for validation
```

### Metadata Format

Each trained model includes metadata:

```json
{
  "model_name": "pneumonia_detector",
  "architecture": "resnet50",
  "num_classes": 3,
  "class_names": ["Normal", "Bacterial Pneumonia", "Viral Pneumonia"],
  "best_val_acc": 94.23,
  "epoch": 47,
  "training_date": "2025-11-22 15:30:45"
}
```

### Weight Verification

The system automatically:
- Calculates MD5 checksums for all weight files
- Verifies integrity on load
- Falls back to ImageNet pretrained if weights are corrupted
- Logs weight loading status

---

## Training Best Practices

### Data Augmentation

Training script includes:
- Random cropping
- Horizontal flipping
- Rotation (±10 degrees)
- Color jittering (brightness, contrast)
- Normalization (ImageNet statistics)

### Hyperparameter Tuning

Recommended starting points:

| Dataset Size | Batch Size | Learning Rate | Epochs |
|--------------|------------|---------------|--------|
| Small (<5K) | 16 | 0.0001 | 100 |
| Medium (5K-50K) | 32 | 0.001 | 50 |
| Large (>50K) | 64 | 0.001 | 25 |

### Training Tips

1. **Use GPU**: Training on CPU will take 10-50x longer
2. **Monitor validation**: Stop if validation accuracy plateaus
3. **Save checkpoints**: Best model saved automatically
4. **Data quality**: Remove corrupted/mislabeled images
5. **Class balance**: Use weighted sampling for imbalanced datasets

### Expected Training Times (RTX 4070)

| Model | Dataset Size | Epochs | Time per Epoch | Total Time |
|-------|-------------|--------|----------------|------------|
| ResNet-50 | 10K images | 50 | ~3 min | ~2.5 hours |
| DenseNet-121 | 20K images | 50 | ~5 min | ~4 hours |
| EfficientNet-B0 | 15K images | 50 | ~4 min | ~3.5 hours |

---

## Deployment with Trained Weights

### 1. Place Weights in Directory

After training, weights are automatically saved to `models/weights/`.

### 2. Start Server

```bash
python main.py
```

### 3. Verify Model Loading

Check logs for:
```
✓ Loaded fine-tuned weights from models\weights\pneumonia_detector.pth (val_acc: 94.23)
```

Or if no weights:
```
ℹ No fine-tuned weights found. Using ImageNet pretrained base.
```

### 4. Test Predictions

```bash
python quick_test.py
```

---

## Monitoring & Evaluation

### Access Dashboard

Navigate to: http://localhost:8000/dashboard

### Check Model Status

```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8000/api/v1/models
```

### Evaluate Model Performance

After training, evaluate on test set:

```python
# Add to train.py for test evaluation
def evaluate_test_set(model, test_loader):
    model.eval()
    correct = 0
    total = 0
    
    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()
    
    return 100. * correct / total
```

---

## Troubleshooting

### Issue: "No training data found"

**Solution**: Verify dataset structure:
```bash
python models\prepare_datasets.py --verify <dataset_id>
```

### Issue: CUDA out of memory

**Solution**: Reduce batch size:
```bash
python models\train.py --model <name> --dataset <path> --batch-size 16
```

### Issue: "Could not load fine-tuned weights"

**Causes**:
- Checkpoint file corrupted
- Model architecture changed
- Wrong number of classes

**Solution**: Retrain or verify checkpoint compatibility

### Issue: Low accuracy after training

**Possible causes**:
- Insufficient training data
- Poor data quality
- Hyperparameters need tuning
- Model too complex/simple for task

**Solution**: 
1. Increase dataset size
2. Tune learning rate
3. Try different architecture
4. Add more augmentation

---

## Production Checklist

Before deploying to production:

- [ ] Train all required models on sufficient data (>5K images per model)
- [ ] Achieve validation accuracy >90% for binary tasks, >80% for multi-class
- [ ] Test on holdout test set
- [ ] Verify weight file integrity (checksums match)
- [ ] Load test with 1000+ concurrent users (locust tests)
- [ ] Monitor GPU memory usage under load
- [ ] Set up proper API key authentication
- [ ] Configure CORS for your domains
- [ ] Enable Prometheus metrics collection
- [ ] Set up alerting for failures
- [ ] Document model versions and performance

---

## Advanced: Custom Model Training

### Add New Model Architecture

1. **Update config.py**:
```python
MODEL_SPECS['my_new_model'] = {
    'architecture': 'resnet50',
    'num_classes': 3,
    'classes': ['Class1', 'Class2', 'Class3'],
    'pretrained': True
}

MODEL_ROUTES['my_new_model'] = '/api/v1/predict/my_model'
```

2. **Train model**:
```bash
python models\train.py --model my_new_model --dataset data\my_dataset
```

3. **Restart server**:
```bash
python main.py
```

### Custom Loss Functions

Modify `train.py` for custom losses:

```python
# Weighted cross-entropy for imbalanced classes
class_weights = torch.tensor([1.0, 2.0, 3.0]).to(device)
criterion = nn.CrossEntropyLoss(weight=class_weights)

# Focal loss for hard examples
from torchvision.ops import sigmoid_focal_loss
```

### Transfer Learning from Other Medical Models

```python
# Load weights from another medical model
pretrained_model = torch.load('external_weights.pth')
model.load_state_dict(pretrained_model, strict=False)

# Fine-tune only final layers
for param in model.parameters():
    param.requires_grad = False
model.fc.requires_grad = True  # Only train classifier
```

---

## References

### Datasets

- **ChestX-ray14**: https://www.kaggle.com/datasets/paultimothymooney/chest-xray-pneumonia
- **ISIC 2019**: https://www.kaggle.com/competitions/isic-2019
- **Diabetic Retinopathy**: https://www.kaggle.com/c/diabetic-retinopathy-detection
- **Brain Tumor MRI**: https://www.kaggle.com/datasets/masoudnickparvar/brain-tumor-mri-dataset

### Papers

- ResNet: "Deep Residual Learning for Image Recognition"
- DenseNet: "Densely Connected Convolutional Networks"
- EfficientNet: "EfficientNet: Rethinking Model Scaling for CNNs"

### Tools

- PyTorch: https://pytorch.org/
- TorchVision: https://pytorch.org/vision/
- Kaggle API: https://github.com/Kaggle/kaggle-api

---

**Need Help?**

- Check logs in `logs/` directory
- Run health check: `python health_check.py`
- Review training history in checkpoint files
- Contact support with model metadata and error logs
