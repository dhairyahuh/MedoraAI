---
license: mit
language:
- en
tags:
- medical-imaging
- federated-learning
- healthcare
- pytorch
- vision-transformer
- x-ray
- mri
- ct-scan
- dermoscopy
library_name: transformers
pipeline_tag: image-classification
---

# 🏥 Medora-Models

**Production Medical AI Models for Federated Learning**

This repository contains pre-trained medical imaging models used by [MedoraAI](https://github.com/TheTusharChopra/MedoraAI) - a privacy-preserving federated learning platform for healthcare.

---

## 📦 Models Included

| Model | Task | Architecture | Input | Classes |
|-------|------|--------------|-------|---------|
| `pneumonia_detector` | Chest X-Ray Analysis | ViT-Base | 224×224 | Normal, Pneumonia |
| `skin_cancer_detector` | Dermoscopy Classification | Swin-Tiny | 224×224 | 7 skin lesion types |
| `diabetic_retinopathy` | Fundus Imaging | DINOv2-Base | 518×518 | 5 DR severity levels |
| `breast_cancer_detector` | Mammogram Analysis | ViT-Base | 224×224 | Benign, Malignant |
| `tumor_detector` | Brain MRI | Swin-Tiny | 224×224 | Glioma, Meningioma, Pituitary, No Tumor |
| `lung_nodule_detector` | Lung CT | ResNet50 | 224×224 | 4 cancer types |
| `fracture_detector` | Bone X-Ray | SigLIP | 224×224 | Fractured, Not Fractured |
| `covid_ct_detector` | COVID-19 CT | ViT-Base | 224×224 | COVID, Non-COVID |
| `ultrasound_classifier` | Breast Ultrasound | ViT-Base | 224×224 | Benign, Malignant, Normal |
| `gi_disease_detector` | Endoscopy | ViT-Small | 224×224 | Tumor, Normal |

---

## 🚀 Usage

### With Transformers

```python
from transformers import AutoModelForImageClassification, AutoProcessor
import torch
from PIL import Image

# Load model
model = AutoModelForImageClassification.from_pretrained(
    "tusharchopra01/Medora-Models",
    subfolder="models/weights/bone_fracture"
)
processor = AutoProcessor.from_pretrained(
    "tusharchopra01/Medora-Models",
    subfolder="models/weights/bone_fracture"
)

# Inference
image = Image.open("xray.jpg")
inputs = processor(images=image, return_tensors="pt")
outputs = model(**inputs)
predicted_class = outputs.logits.argmax(-1).item()
```

### With PyTorch (Direct)

```python
import torch
from PIL import Image
from torchvision import transforms

# Load weights
model = torch.load("models/weights/pneumonia_vit.pth")
model.eval()

# Preprocess
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

image = transform(Image.open("chest_xray.jpg")).unsqueeze(0)
with torch.no_grad():
    output = model(image)
    prediction = output.argmax(dim=1)
```

---

## 📁 Repository Structure

```
Medora-Models/
├── models/
│   ├── weights/
│   │   ├── pneumonia_detector_vit.pth
│   │   ├── skin_cancer/
│   │   ├── bone_fracture/
│   │   ├── covid_ct/
│   │   ├── ultrasound/
│   │   └── ...
│   └── model_manager.py
├── federated_data/
│   └── gradients/           # Federated learning gradients
└── model_pneumonia/         # Pneumonia detection package
```

---

## 🔬 Training Details

| Aspect | Details |
|--------|---------|
| **Framework** | PyTorch 2.x |
| **Base Models** | HuggingFace Transformers (ViT, Swin, DINOv2) |
| **Training Method** | Transfer learning + Federated Learning |
| **Privacy** | Differential Privacy (ε=0.1) |
| **Datasets** | Various medical imaging datasets (see citations) |

---

## ⚠️ Intended Use & Limitations

### Intended For
- Research and educational purposes
- Development of medical AI systems
- Federated learning experiments
- Clinical decision **support** (not replacement)

### Limitations
- **Not FDA approved** - Do not use for clinical diagnosis
- Models trained on limited datasets - may not generalize
- Performance varies across patient populations
- Requires expert validation before any clinical use

---

## 📊 Performance Metrics

Performance on held-out test sets:

| Model | Accuracy | AUC-ROC | F1-Score |
|-------|----------|---------|----------|
| Pneumonia Detector | 94.2% | 0.97 | 0.93 |
| Skin Cancer (Melanoma) | 89.5% | 0.94 | 0.87 |
| Fracture Detector | 92.1% | 0.95 | 0.91 |
| Brain Tumor | 96.3% | 0.98 | 0.95 |

*Note: Metrics are from validation sets and may differ in production.*

---

## 🔗 Related Links

- **Main Project**: [github.com/TheTusharChopra/MedoraAI](https://github.com/TheTusharChopra/MedoraAI)
- **Live Demo**: [http://34.131.184.2](http://34.131.184.2)
- **Documentation**: See project README

---

## 👥 Contributors

**Team AlgoRhythm**
- Tushar Chopra
- Arshdeep Singh
- Dhairya Jain

---

## 📄 License

MIT License - See LICENSE file for details.

---

## 📚 Citation

If you use these models in research, please cite:

```bibtex
@software{medora_models_2026,
  author = {Chopra, Tushar and Singh, Arshdeep and Jain, Dhairya},
  title = {Medora-Models: Federated Medical Imaging Models},
  year = {2026},
  publisher = {Hugging Face},
  url = {https://huggingface.co/tusharchopra01/Medora-Models}
}
```
