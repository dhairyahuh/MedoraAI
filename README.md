# 🏥 MedoraAI

**A Privacy-Preserving Federated Learning Platform for Medical Imaging**

MedoraAI is a production-ready medical image analysis system that enables hospitals to collaboratively improve AI models **without sharing patient data**. The platform combines real-time inference, radiologist-in-the-loop learning, and differential privacy protection.

---

## 🚀 Live Demo

**Deployed on Google Cloud Platform**  
🌐 [http://34.131.184.2](http://34.131.184.2)

---

## 💡 What Makes This Project Novel?

### 1. **True Federated Learning for Healthcare**
Unlike centralized AI systems that require hospitals to upload sensitive patient data, MedoraAI keeps all data local. Only **encrypted gradients** are shared, and they're protected with **Differential Privacy (ε=0.1)** to prevent any patient information leakage.

### 2. **Radiologist-in-the-Loop Training**
AI models don't just predict—they learn. When radiologists review and correct predictions, those corrections are used to **train the model in real-time** using supervised learning. This creates a continuous improvement cycle.

### 3. **Multi-Hospital Collaboration**
Multiple hospitals can contribute to model improvements without ever seeing each other's data. The FedAvg algorithm aggregates learning from all participants to create a more robust global model.

### 4. **Production-Grade Security**
- JWT authentication with RS256 signatures
- AES-256-GCM encryption for data at rest
- HIPAA-compliant audit logging
- Role-based access control

---

## � Deployed Models (10 Medical AI Models on GCP)

| # | Model | Imaging Type | Disease Detection | Architecture |
|---|-------|--------------|-------------------|--------------|
| 1 | **Fracture Detector** | X-Ray | Bone fractures | SigLIP (HuggingFace) |
| 2 | **Pneumonia Detector** | Chest X-Ray | Pneumonia | Vision Transformer |
| 3 | **Skin Cancer Detector** | Dermoscopy | 7 skin cancer types | Swin Transformer |
| 4 | **Diabetic Retinopathy** | Fundus | DR severity grading | DINOv2 |
| 5 | **Brain Tumor Detector** | MRI | Glioma, Meningioma, Pituitary | Swin Transformer |
| 6 | **Lung Cancer Detector** | CT Scan | Adenocarcinoma, Squamous Cell | ResNet50 |
| 7 | **Breast Cancer Detector** | Mammogram | Benign vs Malignant | Vision Transformer |
| 8 | **COVID-19 CT Detector** | CT Scan | COVID vs Non-COVID | ViT (HuggingFace) |
| 9 | **Ultrasound Classifier** | Breast Ultrasound | Benign, Malignant, Normal | ViT (HuggingFace) |
| 10 | **GI Disease Detector** | Endoscopy | Tumor vs Normal | ViT |

---

## ✨ Features Implemented

### 🖼️ Medical Image Inference
- Upload medical images (JPEG, PNG, DICOM)
- Automatic model routing based on image type
- Real-time prediction with confidence scores
- Batch processing support

### 👨‍⚕️ Radiologist Review System
- Web-based review queue for pending predictions
- Confirm, Correct, or Skip workflow
- Ground truth collection for supervised learning
- Review statistics and model accuracy tracking

### 🔗 Federated Learning Pipeline
- Gradient computation on confirmed labels
- Differential Privacy noise injection
- Local gradient storage per hospital
- FedAvg aggregation for model updates
- Privacy budget tracking (epsilon accounting)

### 📊 Dashboard & Monitoring
- Real-time queue status
- Model performance metrics
- Federated learning contributions
- Prometheus metrics endpoint for observability

### � Security Features
- JWT-based API authentication
- AES-256 encryption
- Rate limiting (with Redis support)
- Comprehensive audit logging

### ☁️ Cloud Deployment
- Google Cloud Platform VM deployment
- PostgreSQL database backend
- Nginx reverse proxy
- Systemd service management
- Auto-restart on failure

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI, Python 3.11 |
| Database | PostgreSQL, SQLAlchemy |
| ML | PyTorch, HuggingFace Transformers |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Deployment | Nginx, Gunicorn, Systemd |
| Cloud | Google Cloud Platform (GCP) |

---

## � Project Structure

```
MedoraAI/
├── main.py                    # Application entry point
├── config.py                  # Model specs & configuration
├── api/
│   ├── routes.py              # Inference API
│   ├── radiologist_routes.py  # Review system
│   └── federated_routes.py    # Federated learning
├── models/                    # Model weights & manager
├── federated/                 # FedAvg, DP, storage
├── static/                    # Web interfaces
└── security/                  # JWT, encryption, audit
```

---

## � Quick Start

```bash
# Clone repository
git clone https://github.com/TheTusharChopra/MedoraAI.git
cd MedoraAI

# Setup environment
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 👤 Contributors

**Team AlgoRhythm**

**Tushar Chopra**  
**Arshdeep Singh**\
**Dhairya Jain**  

---

<p align="center">Built for privacy-preserving healthcare AI 🏥</p>

