"""
Configuration settings for Medical Inference Server
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models" / "weights"
STATIC_DIR = BASE_DIR / "static"
LOGS_DIR = BASE_DIR / "logs"
TEST_IMAGES_DIR = STATIC_DIR / "test_images"

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
WORKERS = int(os.getenv("WORKERS", 1))
RELOAD = os.getenv("RELOAD", "False").lower() == "true"

# Queue configuration
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", 10000))
# Concurrency
# REDUCED FOR VM STABILITY (2 vCPUs)
NUM_ASYNC_WORKERS = 1     # Single async worker per process
PROCESS_POOL_WORKERS = 1  # Single heavy model process per worker

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/federated_data/federated.db")

# Model configuration
DEVICE = os.getenv("DEVICE", "cuda" if __import__("torch").cuda.is_available() else "cpu")  # Auto-detect GPU
MODEL_BATCH_SIZE = int(os.getenv("MODEL_BATCH_SIZE", 1))
MODEL_TIMEOUT = int(os.getenv("MODEL_TIMEOUT", 120))  # seconds - increased for GPU + federated training

# Image processing
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".dcm"}
IMAGE_SIZE = (224, 224)  # Standard input size for most models

# API Keys for authentication
VALID_API_KEYS = set(os.getenv("API_KEYS", "dev-key-12345,test-key-67890").split(","))

# Response configuration
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.8))
ENABLE_ENSEMBLE = os.getenv("ENABLE_ENSEMBLE", "False").lower() == "true"
ENSEMBLE_MODELS_COUNT = int(os.getenv("ENSEMBLE_MODELS_COUNT", 3))

# Model routing - Maps disease types to model names
MODEL_ROUTES = {
    'chest_xray': 'pneumonia_detector',
    'fundus': 'diabetic_retinopathy_detector',
    'dermoscopy': 'skin_cancer_detector',
    'mammogram': 'breast_cancer_detector',
    'brain_mri': 'tumor_detector',
    'ct_scan': 'lung_nodule_detector',
    'colonoscopy': 'polyp_detector',
    'cardiac_mri': 'heart_disease_detector',
    'pathology': 'cancer_grading_detector',
    'orthopedic': 'fracture_detector',
    'kidney_ct': 'kidney_stone_detector',
    'liver_mri': 'liver_disease_detector',
    'retinal': 'retinal_disease_detector',
    'endoscopy': 'gi_disease_detector',
    'ultrasound': 'ultrasound_classifier'
}

# Model specifications
MODEL_SPECS = {
    'pneumonia_detector': {
        'architecture': 'vit_base_patch16_224',
        'num_classes': 2,
        'classes': ['Normal', 'Pneumonia'],
        'pretrained': True,
        'weight_file': 'pneumonia_detector_vit.pth'
    },
    'skin_cancer_detector': {
        'architecture': 'swin_tiny_patch4_window7_224',
        'num_classes': 7,
        'classes': ['Actinic-keratoses', 'Basal-cell-carcinoma', 'Benign-keratosis-like-lesions', 'Dermatofibroma', 'Melanocytic-nevi', 'Melanoma', 'Vascular-lesions'],
        'pretrained': True,
        'weight_file': 'skin_cancer/skin_cancer_swin.pth.bin'
    },
    'diabetic_retinopathy_detector': {
        'architecture': 'dinov2_base',
        'num_classes': 5,
        'classes': ['No DR', 'Mild', 'Moderate', 'Severe', 'Proliferative DR'],
        'pretrained': True,
        'weight_file': 'diabetic_retinopathy/model.safetensors',
        'image_size': 518  # DINOv2 uses 518x518
    },
    'breast_cancer_detector': {
        'architecture': 'vit_base_patch16_224',
        'num_classes': 2,
        'classes': ['Benign', 'Malignant'],
        'pretrained': True,
        'weight_file': 'breast_cancer_vit.pth.bin'
    },
    'tumor_detector': {
        'architecture': 'swin_tiny_patch4_window7_224',
        'num_classes': 4,
        'classes': ['Glioma', 'Meningioma', 'Pituitary', 'No Tumor'],
        'pretrained': True,
        'weight_file': 'brain_tumor_swin.pth'
    },
    'lung_nodule_detector': {
        'architecture': 'resnet50_lungai',
        'num_classes': 4,
        'classes': ['Adenocarcinoma', 'Large Cell Carcinoma', 'Normal', 'Squamous Cell Carcinoma'],
        'pretrained': True,
        'weight_file': 'lung_ct_cancer_resnet.pth'
    },
    'polyp_detector': {
        # Actually COVID-19 CT detection (renamed)
        'architecture': 'vit_base_covid_ct',
        'num_classes': 2,
        'classes': ['CT_COVID', 'CT_NonCOVID'],
        'pretrained': True,
        'weight_file': 'covid_ct',  # Directory with HuggingFace model
        'hf_model': 'DunnBC22/vit-base-patch16-224-in21k_covid_19_ct_scans'
    },
    'heart_disease_detector': {
        'architecture': 'resnet50',
        'num_classes': 4,
        'classes': ['Cardiomyopathy', 'Heart Failure', 'Myocardial Infarction', 'Normal'],
        'pretrained': True
    },
    'cancer_grading_detector': {
        'architecture': 'swin_lung_ct',
        'num_classes': 2,
        'classes': ['negative', 'positive'],
        'pretrained': True,
        'weight_file': 'lung_ct_swin',  # Directory with HuggingFace model
        'hf_model': 'oohtmeel/swin-tiny-patch4-finetuned-lung-cancer-ct-scans'
    },
    'fracture_detector': {
        'architecture': 'deta_bone_fracture',
        'num_classes': 1,  # 1 class: "fracture"
        'classes': ['Not Fractured', 'Fractured'],
        'pretrained': True,
        'weight_file': 'bone_fracture_detr',
        'hf_model': 'Judy07/bone-fracture-DETA'
    },
    'kidney_stone_detector': {
        'architecture': 'resnet34',
        'num_classes': 3,
        'classes': ['Stone Present', 'No Stone', 'Undetermined'],
        'pretrained': True
    },
    'liver_disease_detector': {
        'architecture': 'resnet50',
        'num_classes': 4,
        'classes': ['Cirrhosis', 'Fatty Liver', 'Hepatocellular Carcinoma', 'Normal'],
        'pretrained': True
    },
    'retinal_disease_detector': {
        'architecture': 'efficientnet_b0',
        'num_classes': 4,
        'classes': ['Glaucoma', 'AMD', 'Diabetic Retinopathy', 'Normal'],
        'pretrained': True
    },
    'gi_disease_detector': {
        'architecture': 'vit_small_patch16_224',
        'num_classes': 2,
        'classes': ['Tumor', 'Normal'],
        'pretrained': True,
        'weight_file': 'cancer_grading_vit.pth'
    },
    'ultrasound_classifier': {
        'architecture': 'vit_ultrasound',
        'num_classes': 3,
        'classes': ['benign', 'malignant', 'normal'],
        'pretrained': True,
        'weight_file': 'ultrasound',  # Directory with HuggingFace model
        'hf_model': 'sergiopaniego/fine_tuning_vit_custom_dataset_breastcancer-ultrasound-images'
    }
}

# Monitoring
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", 9090))
ENABLE_METRICS = os.getenv("ENABLE_METRICS", "True").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "inference.log"

# Performance thresholds
MAX_RESPONSE_TIME = float(os.getenv("MAX_RESPONSE_TIME", 2.0))  # seconds
MAX_QUEUE_WAIT_TIME = float(os.getenv("MAX_QUEUE_WAIT_TIME", 5.0))  # seconds
MIN_SUCCESS_RATE = float(os.getenv("MIN_SUCCESS_RATE", 0.999))  # 99.9%

# Circuit breaker configuration
CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", 10))
CIRCUIT_BREAKER_TIMEOUT = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", 60))  # seconds
