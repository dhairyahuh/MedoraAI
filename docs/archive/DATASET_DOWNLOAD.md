# Dataset and Model Weights Download Instructions

Due to GitHub file size limitations, the following large files are **not included** in this repository:

## 📦 Required Downloads

### 1. **Model Weights** (~800MB)
Location: `models/weights/`

Download pre-trained model weights from:
- [Google Drive](https://drive.google.com) - Upload your weights here
- [Hugging Face](https://huggingface.co) - Recommended for model hosting

Models needed:
- `bone_fracture_model.pth`
- `brain_tumor_model.pth`
- `breast_cancer_model.pth`
- `chest_xray_model.pth`
- `diabetic_retinopathy_model.pth`
- `lung_cancer_model.pth`
- `skin_lesion_model.pth`
- And others (see `models/model_definitions.py`)

### 2. **Dataset Images** (~400MB)
Location: `dataset images/`

Download medical imaging datasets from:
- **NIH Chest X-Ray**: [Kaggle](https://www.kaggle.com/nih-chest-xrays/data)
- **Skin Lesions**: [ISIC Archive](https://www.isic-archive.com/)
- **Diabetic Retinopathy**: [Kaggle](https://www.kaggle.com/c/diabetic-retinopathy-detection)
- **Breast Ultrasound**: [Kaggle](https://www.kaggle.com/datasets/aryashah2k/breast-ultrasound-images-dataset)
- **Brain MRI**: [Kaggle](https://www.kaggle.com/datasets/masoudnickparvar/brain-tumor-mri-dataset)

### 3. **Test Images** (Optional)
Location: `static/test_images/`

Sample medical images for testing the inference system.

## 🚀 Quick Setup

After cloning this repository:

```bash
# 1. Create necessary directories
mkdir "dataset images"
mkdir models/weights
mkdir static/test_images
mkdir uploads

# 2. Download and extract datasets to "dataset images/"
# 3. Download and place model weights in models/weights/
# 4. Install dependencies
pip install -r requirements.txt

# 5. Start the server
python main.py
```

## 📝 Alternative: Use Pretrained Models

The system can download models automatically from Hugging Face:

```bash
python download_additional_models.py
```

## 💡 Note

For production deployment, model weights should be:
- Stored in cloud storage (S3, Azure Blob, Google Cloud Storage)
- Downloaded on first run
- Cached locally for performance

The current `.gitignore` excludes:
- `*.pth` (PyTorch weights)
- `*.jpg`, `*.png` (images)
- `*.db` (databases)
- Large dataset folders
