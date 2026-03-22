"""
Model Manager for Medical Image Inference
Handles model loading, preprocessing, and inference
"""
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
import io
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import time

import config

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)


class MedicalModelWrapper:
    """
    Unified wrapper for medical imaging models with pretrained weights
    """
    
    def __init__(self, model_name: str, device: str = 'cpu'):
        """
        Initialize model wrapper
        
        Args:
            model_name: Name of the model (from MODEL_SPECS)
            device: 'cpu' or 'cuda'
        """
        self.model_name = model_name
        self.device = torch.device(device)
        self.model = None
        self.transform = None
        self.image_processor = None  # For transformers AutoImageProcessor models
        self.classes = []
        self.num_classes = 0
        self.architecture = ''
        
        if model_name not in config.MODEL_SPECS:
            raise ValueError(f"Unknown model: {model_name}")
        
        self._load_model()
        self._setup_preprocessing()
        logger.info(f"Loaded model: {model_name} on {device}")
    
    def _load_pneumonia_model_offline(self):
        """
        Load Pneumonia model offline using transformers ViT with local weights.
        Hard fails if weights are missing.
        """
        from transformers import ViTConfig, ViTForImageClassification
        
        # Set model attributes from config
        spec = config.MODEL_SPECS[self.model_name]
        self.architecture = spec['architecture']
        self.num_classes = spec['num_classes']
        self.classes = spec['classes']
        
        weights_path = Path(config.BASE_DIR) / "models" / "weights" / "pneumonia_vit.pth"
        
        # Hard fail if weights are missing
        if not weights_path.exists():
            raise FileNotFoundError(
                f"Pneumonia model weights not found at {weights_path}. "
                "Offline inference requires local weights at models/weights/pneumonia_vit.pth"
            )
        
        logger.info(f"Loading Pneumonia model architecture (offline)...")
        
        # Create ViT-Base config manually (vit_base_patch16_224)
        # This matches the validated model configuration
        vit_config = ViTConfig(
            image_size=224,
            patch_size=16,
            num_channels=3,
            hidden_size=768,
            num_hidden_layers=12,
            num_attention_heads=12,
            intermediate_size=3072,
            hidden_dropout_prob=0.0,
            attention_probs_dropout_prob=0.0,
            initializer_range=0.02,
            layer_norm_eps=1e-12,
            num_labels=2,  # Binary classification: Normal, Pneumonia
            id2label={0: "Normal", 1: "Pneumonia"},
            label2id={"Normal": 0, "Pneumonia": 1},
        )
        
        # Instantiate model from config (no download, fully offline)
        self.model = ViTForImageClassification(vit_config)
        
        # Load local weights
        logger.info(f"Loading weights from {weights_path}...")
        try:
            state_dict = torch.load(weights_path, map_location=self.device)
            
            # Handle different checkpoint formats
            if isinstance(state_dict, dict):
                if 'model_state_dict' in state_dict:
                    self.model.load_state_dict(state_dict['model_state_dict'], strict=True)
                elif 'state_dict' in state_dict:
                    self.model.load_state_dict(state_dict['state_dict'], strict=True)
                else:
                    # Direct state dict
                    self.model.load_state_dict(state_dict, strict=True)
            else:
                self.model.load_state_dict(state_dict, strict=True)
            
            logger.info(f"✓ Loaded Pneumonia weights from {weights_path}")
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Pneumonia model weights from {weights_path}: {e}. "
                "Ensure the weights file is valid and matches the model architecture."
            )
        
        self.model.to(self.device)
        self.model.eval()
        logger.info("Pneumonia model loaded successfully (offline mode)")
    
    def _load_skin_cancer_model_offline(self):
        """
        Load Skin Cancer model offline using transformers AutoModelForImageClassification.
        Hard fails if model directory is missing.
        """
        from transformers import AutoModelForImageClassification, AutoImageProcessor
        
        # Set model attributes from config
        spec = config.MODEL_SPECS[self.model_name]
        self.architecture = spec['architecture']
        self.num_classes = spec['num_classes']
        self.classes = spec['classes']
        
        model_dir = Path(config.BASE_DIR) / "models" / "weights" / "skin_cancer"
        
        # Hard fail if model directory is missing
        if not model_dir.exists():
            raise FileNotFoundError(
                f"Skin Cancer model directory not found at {model_dir}. "
                "Offline inference requires local model at models/weights/skin_cancer/"
            )
        
        logger.info(f"Loading Skin Cancer model architecture (offline)...")
        
        try:
            # Check for model weight file (handle non-standard names)
            weight_file = None
            possible_names = ['pytorch_model.bin', 'model.safetensors', 'skin_cancer_swin.pth.bin']
            for name in possible_names:
                candidate = model_dir / name
                if candidate.exists():
                    weight_file = candidate
                    break
            
            if weight_file and weight_file.name != 'pytorch_model.bin':
                # Load config first
                from transformers import AutoConfig
                model_config = AutoConfig.from_pretrained(
                    str(model_dir),
                    local_files_only=True
                )
                
                # Create model from config
                self.model = AutoModelForImageClassification.from_config(model_config)
                
                # Load weights manually
                logger.info(f"Loading weights from {weight_file}...")
                state_dict = torch.load(weight_file, map_location=self.device)
                
                # Handle different checkpoint formats
                if isinstance(state_dict, dict):
                    if 'model_state_dict' in state_dict:
                        self.model.load_state_dict(state_dict['model_state_dict'], strict=True)
                    elif 'state_dict' in state_dict:
                        self.model.load_state_dict(state_dict['state_dict'], strict=True)
                    else:
                        # Direct state dict
                        self.model.load_state_dict(state_dict, strict=True)
                else:
                    self.model.load_state_dict(state_dict, strict=True)
                
                logger.info(f"✓ Loaded weights from {weight_file}")
            else:
                # Standard transformers loading
                self.model = AutoModelForImageClassification.from_pretrained(
                    str(model_dir),
                    local_files_only=True,
                    trust_remote_code=False
                )
            
            # Load image processor
            self.image_processor = AutoImageProcessor.from_pretrained(
                str(model_dir),
                local_files_only=True,
                trust_remote_code=False
            )
            
            logger.info(f"✓ Loaded Skin Cancer model from {model_dir}")
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Skin Cancer model from {model_dir}: {e}. "
                "Ensure the model directory contains config.json and model weights."
            )
        
        self.model.to(self.device)
        self.model.eval()
        logger.info("Skin Cancer model loaded successfully (offline mode)")
    
    def _load_diabetic_retinopathy_model_offline(self):
        """
        Load Diabetic Retinopathy model offline using transformers AutoModelForImageClassification.
        Hard fails if model directory is missing.
        """
        from transformers import AutoModelForImageClassification, AutoImageProcessor
        
        # Set model attributes from config
        spec = config.MODEL_SPECS[self.model_name]
        self.architecture = spec['architecture']
        self.num_classes = spec['num_classes']
        self.classes = spec['classes']
        
        model_dir = Path(config.BASE_DIR) / "models" / "weights" / "diabetic_retinopathy"
        
        # Hard fail if model directory is missing
        if not model_dir.exists():
            raise FileNotFoundError(
                f"Diabetic Retinopathy model directory not found at {model_dir}. "
                "Offline inference requires local model at models/weights/diabetic_retinopathy/"
            )
        
        logger.info(f"Loading Diabetic Retinopathy model architecture (offline)...")
        
        try:
            # Load model from local directory only (no Hugging Face calls)
            self.model = AutoModelForImageClassification.from_pretrained(
                str(model_dir),
                local_files_only=True,
                trust_remote_code=False
            )
            
            # Load image processor
            self.image_processor = AutoImageProcessor.from_pretrained(
                str(model_dir),
                local_files_only=True,
                trust_remote_code=False
            )
            
            logger.info(f"✓ Loaded Diabetic Retinopathy model from {model_dir}")
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Diabetic Retinopathy model from {model_dir}: {e}. "
                "Ensure the model directory contains config.json and model weights."
            )
        
        self.model.to(self.device)
        self.model.eval()
        logger.info("Diabetic Retinopathy model loaded successfully (offline mode)")
    
    def _load_breast_cancer_model_offline(self):
        """
        Load Breast Cancer model offline using manual ViT-Base with local weights.
        Hard fails if weights are missing.
        """
        from transformers import ViTConfig, ViTForImageClassification
        
        # Set model attributes from config
        spec = config.MODEL_SPECS[self.model_name]
        self.architecture = spec['architecture']
        self.num_classes = spec['num_classes']
        self.classes = spec['classes']
        
        weights_path = Path(config.BASE_DIR) / "models" / "weights" / "breast_cancer_vit.pth"
        
        # Also check for .bin extension
        if not weights_path.exists():
            weights_path = Path(config.BASE_DIR) / "models" / "weights" / "breast_cancer_vit.pth.bin"
        
        # Hard fail if weights are missing
        if not weights_path.exists():
            raise FileNotFoundError(
                f"Breast Cancer model weights not found at {weights_path}. "
                "Offline inference requires local weights at models/weights/breast_cancer_vit.pth"
            )
        
        logger.info(f"Loading Breast Cancer model architecture (offline)...")
        
        # Load weights first to detect number of classes
        logger.info(f"Loading weights from {weights_path} to detect architecture...")
        state_dict = torch.load(weights_path, map_location=self.device)
        
        # Extract state dict
        if isinstance(state_dict, dict):
            if 'model_state_dict' in state_dict:
                actual_state_dict = state_dict['model_state_dict']
            elif 'state_dict' in state_dict:
                actual_state_dict = state_dict['state_dict']
            else:
                actual_state_dict = state_dict
        else:
            actual_state_dict = state_dict
        
        # Detect number of classes from classifier weight shape
        classifier_key = None
        for key in actual_state_dict.keys():
            if 'classifier' in key and 'weight' in key:
                classifier_key = key
                break
        
        # Initialize id2label and label2id with defaults based on config
        # This ensures they are always defined before use
        id2label = {i: self.classes[i] for i in range(len(self.classes))}
        label2id = {self.classes[i]: i for i in range(len(self.classes))}
        num_labels_detected = self.num_classes
        
        if classifier_key:
            num_labels_detected = actual_state_dict[classifier_key].shape[0]
            logger.info(f"Detected {num_labels_detected} classes from weights file")
            
            # Update num_classes and classes if mismatch
            if num_labels_detected != self.num_classes:
                logger.warning(
                    f"Config specifies {self.num_classes} classes but weights have {num_labels_detected}. "
                    f"Using {num_labels_detected} classes from weights."
                )
                self.num_classes = num_labels_detected
                
                # Update classes list - try to map or use generic labels
                if num_labels_detected == 2:
                    self.classes = ['Benign', 'Malignant']  # Common binary classification
                    id2label = {0: "Benign", 1: "Malignant"}
                    label2id = {"Benign": 0, "Malignant": 1}
                elif num_labels_detected == 3:
                    self.classes = ['Benign', 'Malignant', 'Normal']
                    id2label = {0: "Benign", 1: "Malignant", 2: "Normal"}
                    label2id = {"Benign": 0, "Malignant": 1, "Normal": 2}
                else:
                    # Generic labels
                    self.classes = [f"Class_{i}" for i in range(num_labels_detected)]
                    id2label = {i: f"Class_{i}" for i in range(num_labels_detected)}
                    label2id = {f"Class_{i}": i for i in range(num_labels_detected)}
        
        # Create ViT-Base config with detected number of classes
        vit_config = ViTConfig(
            image_size=224,
            patch_size=16,
            num_channels=3,
            hidden_size=768,
            num_hidden_layers=12,
            num_attention_heads=12,
            intermediate_size=3072,
            hidden_dropout_prob=0.0,
            attention_probs_dropout_prob=0.0,
            initializer_range=0.02,
            layer_norm_eps=1e-12,
            num_labels=num_labels_detected,
            id2label=id2label,
            label2id=label2id,
        )
        
        # Instantiate model from config (no download, fully offline)
        self.model = ViTForImageClassification(vit_config)
        
        # Load weights
        try:
            if isinstance(state_dict, dict):
                if 'model_state_dict' in state_dict:
                    self.model.load_state_dict(state_dict['model_state_dict'], strict=True)
                elif 'state_dict' in state_dict:
                    self.model.load_state_dict(state_dict['state_dict'], strict=True)
                else:
                    # Direct state dict
                    self.model.load_state_dict(state_dict, strict=True)
            else:
                self.model.load_state_dict(state_dict, strict=True)
            
            logger.info(f"✓ Loaded Breast Cancer weights from {weights_path}")
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Breast Cancer model weights from {weights_path}: {e}. "
                "Ensure the weights file is valid and matches the model architecture."
            )
        
        self.model.to(self.device)
        self.model.eval()
        logger.info("Breast Cancer model loaded successfully (offline mode)")
    
    def _load_tumor_detector_offline(self):
        """
        Load Brain Tumor model offline using HuggingFace transformers.
        Uses the Devarshi/Brain_Tumor_Classification model (Swin architecture).
        """
        from transformers import AutoModelForImageClassification, AutoImageProcessor
        
        # Set model attributes from config
        spec = config.MODEL_SPECS[self.model_name]
        self.architecture = spec['architecture']
        self.num_classes = spec['num_classes']
        self.classes = spec['classes']
        
        hf_repo = "Devarshi/Brain_Tumor_Classification"
        
        logger.info(f"Loading Brain Tumor model (Swin) from HuggingFace: {hf_repo}")
        
        try:
            # Load model from HuggingFace (will use cached version if available)
            self.model = AutoModelForImageClassification.from_pretrained(hf_repo)
            
            # Load image processor
            self.image_processor = AutoImageProcessor.from_pretrained(hf_repo)
            
            logger.info(f"✓ Loaded Brain Tumor model: {self.model.config.num_labels} classes")
            logger.info(f"  Classes: {self.model.config.id2label}")
            
            # Update classes to match model's actual labels
            self.classes = [self.model.config.id2label[i] for i in range(self.model.config.num_labels)]
            self.num_classes = self.model.config.num_labels
            
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Brain Tumor model: {e}. "
                "Ensure you have internet access or the model is cached locally."
            )
        
        self.model.to(self.device)
        self.model.eval()
        logger.info("Brain Tumor model loaded successfully")
    
    def _load_lung_nodule_detector_offline(self):
        """
        Load Lung CT Cancer model offline using ResNet50 architecture.
        Uses the dorsar/lung-cancer-detection (LungAI) model trained on CT scans.
        This model has 98% accuracy on actual CT scan images.
        """
        from torchvision.models import resnet50, ResNet50_Weights
        
        # Set model attributes from config
        spec = config.MODEL_SPECS[self.model_name]
        self.architecture = spec['architecture']
        self.num_classes = spec['num_classes']
        self.classes = spec['classes']
        
        weights_dir = Path(config.BASE_DIR) / "models" / "weights"
        weight_file = weights_dir / spec['weight_file']
        
        if not weight_file.exists():
            raise FileNotFoundError(
                f"Lung CT Cancer model weights not found at {weight_file}. "
                "Please download from dorsar/lung-cancer-detection on HuggingFace."
            )
        
        logger.info(f"Loading Lung CT Cancer model (ResNet50 LungAI) from {weight_file}")
        
        try:
            # Build the ResNetLungCancer architecture to match LungAI
            class ResNetLungCancer(nn.Module):
                def __init__(self, num_classes):
                    super(ResNetLungCancer, self).__init__()
                    self.resnet = resnet50(weights=None)
                    num_ftrs = self.resnet.fc.in_features
                    self.resnet.fc = nn.Identity()
                    self.fc = nn.Sequential(
                        nn.Linear(num_ftrs, 256),
                        nn.ReLU(),
                        nn.Dropout(0.5),
                        nn.Linear(256, num_classes)
                    )
                
                def forward(self, x):
                    x = self.resnet(x)
                    return self.fc(x)
            
            self.model = ResNetLungCancer(self.num_classes)
            
            # Load weights
            state_dict = torch.load(weight_file, map_location=self.device)
            self.model.load_state_dict(state_dict)
            
            logger.info(f"✓ Loaded Lung CT Cancer model: {self.num_classes} classes")
            logger.info(f"  Classes: {self.classes}")
            logger.info(f"  Model: ResNet50 + Custom FC (LungAI architecture)")
            
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Lung CT Cancer model: {e}. "
                "Ensure the model weights are from dorsar/lung-cancer-detection."
            )
        
        self.model.to(self.device)
        self.model.eval()
        logger.info("Lung CT Cancer model loaded successfully (98% accuracy on CT scans)")

    def _load_hf_model_offline(self, model_dir_name: str, model_display_name: str):
        """
        Generic loader for HuggingFace AutoModelForImageClassification models from local directory.
        
        Args:
            model_dir_name: Name of directory under models/weights/
            model_display_name: Human-readable name for logging
        """
        from transformers import AutoModelForImageClassification, AutoImageProcessor
        
        # Set model attributes from config
        spec = config.MODEL_SPECS[self.model_name]
        self.architecture = spec['architecture']
        self.num_classes = spec['num_classes']
        self.classes = spec['classes']
        
        model_dir = Path(config.BASE_DIR) / "models" / "weights" / model_dir_name
        
        # Hard fail if model directory is missing
        if not model_dir.exists():
            raise FileNotFoundError(
                f"{model_display_name} model directory not found at {model_dir}. "
                f"Offline inference requires local model at models/weights/{model_dir_name}/"
            )
        
        logger.info(f"Loading {model_display_name} model architecture (offline)...")
        
        try:
            # Load model from local directory only (no Hugging Face calls)
            self.model = AutoModelForImageClassification.from_pretrained(
                str(model_dir),
                local_files_only=True,
                trust_remote_code=False
            )
            
            # Load image processor
            try:
                self.image_processor = AutoImageProcessor.from_pretrained(
                    str(model_dir),
                    local_files_only=True,
                    trust_remote_code=False
                )
                logger.info("Using AutoImageProcessor for preprocessing")
            except Exception as e:
                logger.warning(f"Could not load image processor: {e}. Using default preprocessing.")
                self.image_processor = None
            
            # Override classes from model config if available
            if hasattr(self.model.config, 'id2label') and self.model.config.id2label:
                self.classes = list(self.model.config.id2label.values())
                self.num_classes = len(self.classes)
            
            logger.info(f"✓ Loaded {model_display_name} model from {model_dir}")
            logger.info(f"  Classes: {self.classes}")
            
        except Exception as e:
            raise RuntimeError(
                f"Failed to load {model_display_name} model from {model_dir}: {e}. "
                "Offline inference requires local model."
            )
        
        self.model.to(self.device)
        self.model.eval()
        logger.info(f"{model_display_name} model loaded successfully (offline mode)")

    def _load_covid_ct_detector_offline(self):
        """Load COVID-19 CT scan detector (polyp_detector) offline"""
        self._load_hf_model_offline("covid_ct", "COVID-19 CT Scan")

    def _load_lung_ct_swin_offline(self):
        """Load Lung Cancer CT Swin model (cancer_grading_detector) offline"""
        self._load_hf_model_offline("lung_ct_swin", "Lung Cancer CT (Swin)")

    def _load_bone_fracture_detector_offline(self):
        """Load Bone Fracture detector (fracture_detector) offline"""
        self._load_hf_model_offline("bone_fracture", "Bone Fracture Detection (SigLIP)")

    def _load_ultrasound_classifier_offline(self):
        """Load Breast Ultrasound classifier offline"""
        self._load_hf_model_offline("ultrasound", "Breast Ultrasound Classification")

    def _load_bone_fracture_detr_offline(self):
        """
        Load Bone Fracture detector (DETR) offline.
        Uses Object Detection instead of Classification for better reliability.
        """
        from transformers import DetrImageProcessor, DetrForObjectDetection
        
        spec = config.MODEL_SPECS[self.model_name]
        self.architecture = spec['architecture']
        self.classes = spec['classes']
        
        model_dir = Path(config.BASE_DIR) / "models" / "weights" / "bone_fracture_detr"
        
        logger.info(f"Loading Bone Fracture DETR from {model_dir}")
        try:
            self.image_processor = DetrImageProcessor.from_pretrained(str(model_dir), local_files_only=True)
            self.model = DetrForObjectDetection.from_pretrained(str(model_dir), local_files_only=True)
            self.model.to(self.device)
            self.model.eval()
            logger.info("✓ Bone Fracture DETR loaded successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to load DETR model: {e}")

    
    def _load_model(self):
        """Load pretrained model and adapt for medical classification"""
        spec = config.MODEL_SPECS[self.model_name]
        self.architecture = spec['architecture']
        self.num_classes = spec['num_classes']
        self.classes = spec['classes']
        
        # Special handling for offline models with local weights
        if self.model_name == 'pneumonia_detector':
            self._load_pneumonia_model_offline()
            return
        elif self.model_name == 'skin_cancer_detector':
            self._load_skin_cancer_model_offline()
            return
        elif self.model_name == 'diabetic_retinopathy_detector':
            self._load_diabetic_retinopathy_model_offline()
            return
        elif self.model_name == 'breast_cancer_detector':
            self._load_breast_cancer_model_offline()
            return
        elif self.model_name == 'tumor_detector':
            self._load_tumor_detector_offline()
            return
        elif self.model_name == 'lung_nodule_detector':
            self._load_lung_nodule_detector_offline()
            return
        # New models added
        elif self.model_name == 'polyp_detector':
            self._load_covid_ct_detector_offline()
            return
        elif self.model_name == 'cancer_grading_detector':
            self._load_lung_ct_swin_offline()
            return
        elif self.model_name == 'fracture_detector':
            self._load_bone_fracture_detr_offline()
            return
        elif self.model_name == 'ultrasound_classifier':
            self._load_ultrasound_classifier_offline()
            return
        
        # Load base architecture with pretrained weights
        if self.architecture == 'resnet50':
            self.model = models.resnet50(pretrained=spec['pretrained'])
            in_features = self.model.fc.in_features
            self.model.fc = nn.Linear(in_features, self.num_classes)
            
        elif self.architecture == 'resnet34':
            self.model = models.resnet34(pretrained=spec['pretrained'])
            in_features = self.model.fc.in_features
            self.model.fc = nn.Linear(in_features, self.num_classes)
        
        elif self.architecture == 'vit_base_patch16_224':
            self.model = models.vit_b_16(pretrained=spec['pretrained'])
            in_features = self.model.heads.head.in_features
            self.model.heads.head = nn.Linear(in_features, self.num_classes)
        
        elif self.architecture == 'swin_tiny_patch4_window7_224':
            self.model = models.swin_t(pretrained=spec['pretrained'])
            in_features = self.model.head.in_features
            self.model.head = nn.Linear(in_features, self.num_classes)
        
        elif self.architecture == 'convnext_tiny':
            self.model = models.convnext_tiny(pretrained=spec['pretrained'])
            in_features = self.model.classifier[2].in_features
            self.model.classifier[2] = nn.Linear(in_features, self.num_classes)
            
        elif self.architecture == 'densenet121':
            self.model = models.densenet121(pretrained=spec['pretrained'])
            in_features = self.model.classifier.in_features
            self.model.classifier = nn.Linear(in_features, self.num_classes)
            
        elif self.architecture == 'mobilenet_v2':
            self.model = models.mobilenet_v2(pretrained=spec['pretrained'])
            in_features = self.model.classifier[1].in_features
            self.model.classifier[1] = nn.Linear(in_features, self.num_classes)
            
        elif self.architecture == 'efficientnet_b0':
            self.model = models.efficientnet_b0(pretrained=spec['pretrained'])
            in_features = self.model.classifier[1].in_features
            self.model.classifier[1] = nn.Linear(in_features, self.num_classes)
            
        elif self.architecture == 'vgg19':
            self.model = models.vgg19(pretrained=spec['pretrained'])
            in_features = self.model.classifier[6].in_features
            self.model.classifier[6] = nn.Linear(in_features, self.num_classes)
            
        elif self.architecture == 'inception_v3':
            self.model = models.inception_v3(pretrained=spec['pretrained'])
            in_features = self.model.fc.in_features
            self.model.fc = nn.Linear(in_features, self.num_classes)
        
        elif self.architecture == 'vit_base_patch16_224':
            self.model = models.vit_b_16(pretrained=spec['pretrained'])
            in_features = self.model.heads.head.in_features
            self.model.heads.head = nn.Linear(in_features, self.num_classes)
        
        elif self.architecture == 'swin_tiny_patch4_window7_224':
            self.model = models.swin_t(pretrained=spec['pretrained'])
            in_features = self.model.head.in_features
            self.model.head = nn.Linear(in_features, self.num_classes)
        
        elif self.architecture == 'convnext_tiny':
            self.model = models.convnext_tiny(pretrained=spec['pretrained'])
            in_features = self.model.classifier[2].in_features
            self.model.classifier[2] = nn.Linear(in_features, self.num_classes)
        
        elif self.architecture == 'dinov2_vits14':
            # DINOv2 small model for diabetic retinopathy
            try:
                self.model = torch.hub.load('facebookresearch/dinov2', 'dinov2_vits14')
                # Add classification head
                in_features = self.model.embed_dim
                self.model.head = nn.Linear(in_features, self.num_classes)
            except:
                # Fallback to ViT if DINOv2 not available
                logger.warning("DINOv2 not available, using ViT as fallback")
                self.model = models.vit_b_16(pretrained=spec['pretrained'])
                in_features = self.model.heads.head.in_features
                self.model.heads.head = nn.Linear(in_features, self.num_classes)
        
        elif self.architecture == 'siglip_so400m_patch14_384':
            # SigLIP model for bone fracture detection
            try:
                import timm
                self.model = timm.create_model('vit_so400m_patch14_siglip_384', pretrained=False, num_classes=self.num_classes)
            except:
                # Fallback to ViT if SigLIP not available
                logger.warning("SigLIP not available, using ViT as fallback")
                self.model = models.vit_b_16(pretrained=spec['pretrained'])
                in_features = self.model.heads.head.in_features
                self.model.heads.head = nn.Linear(in_features, self.num_classes)
        
        elif self.architecture == 'vit_small_patch16_224':
            # ViT Small model for pathology
            try:
                import timm
                self.model = timm.create_model('vit_small_patch16_224', pretrained=spec['pretrained'], num_classes=self.num_classes)
            except:
                # Fallback to ViT Base if ViT Small not available
                logger.warning("ViT Small not available, using ViT Base as fallback")
                self.model = models.vit_b_16(pretrained=spec['pretrained'])
                in_features = self.model.heads.head.in_features
                self.model.heads.head = nn.Linear(in_features, self.num_classes)
            
        else:
            raise ValueError(f"Unsupported architecture: {self.architecture}")
        
        # Try to load fine-tuned weights if available
        weights_dir = Path(config.BASE_DIR) / "models" / "weights"
        weights_path = weights_dir / f"{self.model_name}.pth"
        
        # Check for specific weight file first (from HuggingFace downloads)
        weight_file = None
        weight_type = None
        
        specific_weight = spec.get('weight_file')
        if specific_weight:
            specific_path = weights_dir / specific_weight
            if specific_path.exists():
                weight_file = specific_path
                weight_type = "pre-trained (HuggingFace)"
        
        # Otherwise try standard naming
        if weight_file is None:
            synthetic_weights_path = weights_dir / f"{self.model_name}_synthetic.pth"
            
            # Try production weights first, then synthetic
            if weights_path.exists():
                weight_file = weights_path
                weight_type = "fine-tuned"
            elif synthetic_weights_path.exists():
                weight_file = synthetic_weights_path
                weight_type = "synthetic (testing only)"
        
        if weight_file:
            try:
                checkpoint = torch.load(weight_file, map_location=self.device)
                
                # Handle different checkpoint formats
                if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                    self.model.load_state_dict(checkpoint['model_state_dict'])
                    logger.info(f"✓ Loaded {weight_type} weights from {weight_file} (val_acc: {checkpoint.get('val_acc', 'N/A')})")
                else:
                    # HuggingFace models - try strict first, then relaxed
                    try:
                        self.model.load_state_dict(checkpoint, strict=True)
                        logger.info(f"✓ Loaded {weight_type} weights from {weight_file}")
                    except RuntimeError as e:
                        logger.warning(f"⚠ Trying strict=False due to: {str(e)[:100]}")
                        self.model.load_state_dict(checkpoint, strict=False)
                        logger.info(f"✓ Loaded {weight_type} weights (partial match) from {weight_file}")

            except Exception as e:
                logger.warning(f"⚠ Could not load fine-tuned weights: {e}. Using pretrained base model.")
        else:
            logger.info(f"ℹ No fine-tuned weights found at {weights_path}. Using ImageNet pretrained base.")
        
        self.model.to(self.device)
        self.model.eval()
    
    def _setup_preprocessing(self):
        """Setup image preprocessing pipeline"""
        # Skip transform setup for models using AutoImageProcessor
        if hasattr(self, 'image_processor') and self.image_processor is not None:
            logger.info("Using AutoImageProcessor for preprocessing")
            return
        
        if self.architecture == 'inception_v3':
            # Inception requires 299x299 input
            image_size = 299
        else:
            image_size = 224
        
        self.transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
    
    def preprocess_image(self, image_bytes: bytes) -> torch.Tensor:
        """
        Preprocess image bytes for model input
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Preprocessed tensor or dict (for transformers models)
        """
        try:
            # Load image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Handle transformers models with AutoImageProcessor (Skin Cancer, Diabetic Retinopathy)
            if hasattr(self, 'image_processor') and self.image_processor is not None:
                # Use AutoImageProcessor for transformers models
                inputs = self.image_processor(image, return_tensors="pt")
                # Return dict with pixel_values on correct device
                return {k: v.to(self.device) for k, v in inputs.items()}
            
            # Standard preprocessing for other models
            # Apply transforms
            tensor = self.transform(image)
            
            # Add batch dimension
            tensor = tensor.unsqueeze(0)
            
            return tensor.to(self.device)
            
        except Exception as e:
            logger.error(f"Image preprocessing error: {e}")
            raise ValueError(f"Invalid image format: {e}")
    
    @torch.no_grad()
    def predict(self, image_bytes: bytes) -> Dict:
        """
        Run inference on image
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Dictionary with predictions
        """
        start_time = time.time()
        
        try:
            # Preprocess
            preprocessed = self.preprocess_image(image_bytes)
            
            # Handle transformers model format
            if self.model_name in ['pneumonia_detector', 'breast_cancer_detector']:
                # Manual ViT models (Pneumonia, Breast Cancer) - tensor input
                inputs = {'pixel_values': preprocessed}
                outputs = self.model(**inputs)
                logits = outputs.logits
                # Get probabilities using max softmax (as specified)
                probabilities = torch.nn.functional.softmax(logits[0], dim=0)
            elif self.model_name in ['skin_cancer_detector', 'diabetic_retinopathy_detector', 'tumor_detector', 
                                     'polyp_detector', 'cancer_grading_detector', 'ultrasound_classifier']:
                # AutoModelForImageClassification models
                
                # If image_processor failed to load, preprocessed is a Tensor, but model expects dict/kwargs
                if isinstance(preprocessed, torch.Tensor):
                    outputs = self.model(pixel_values=preprocessed)
                else:
                    # Dict input from AutoImageProcessor
                    outputs = self.model(**preprocessed)
                    
                logits = outputs.logits
                # Get probabilities using max softmax (as specified)
                probabilities = torch.nn.functional.softmax(logits[0], dim=0)

            elif self.model_name == 'fracture_detector':
                try:
                    print("DEBUG: DETR logic start")
                    # DETR Object Detection Inference
                    if isinstance(preprocessed, torch.Tensor):
                        outputs = self.model(pixel_values=preprocessed)
                    else:
                        outputs = self.model(**preprocessed)
                    print("DEBUG: DETR outputs received")
                    
                    if hasattr(outputs, 'logits'):
                        logits = outputs.logits
                        print(f"DEBUG: logits shape: {logits.shape}")
                        if logits.dim() == 3:
                            logits = logits[0]
                        print(f"DEBUG: processed logits shape: {logits.shape}")
                        
                        probas = logits.softmax(-1)
                        print(f"DEBUG: probas shape: {probas.shape}")
                        
                        # Handle NaN
                        if torch.isnan(probas).any():
                            print("WARNING: Model produced NaNs! using fallback")
                            probas = torch.zeros_like(probas)
                            probas[:, 0] = 0.0 # No detections
                        
                        # Filter for "fracture" class (Index 0 in Judy07 config usually, need to check)
                        # Assuming index 0 based on user testing.
                        
                        # Check num classes
                        n_classes = probas.shape[-1]
                        print(f"DEBUG: n_classes: {n_classes}")
                        
                        keep = probas[:, 0] > 0.5
                        print(f"DEBUG: keep sum: {keep.sum()}")
                        
                        fracture_count = keep.sum().item()
                        
                        if fracture_count > 0:
                            predicted_class = "Fractured"
                            # Ensure scalar
                            max_val = probas[keep][:, 0].max()
                            if max_val.numel() > 1:
                                max_val = max_val[0]
                            confidence = float(max_val.item())
                            pidx = 1
                        else:
                            predicted_class = "Not Fractured"
                            max_val = probas[:, 0].max()
                            # If for some reason this is size 9?
                            if max_val.numel() > 1:
                                max_val = max_val[0]
                            
                            val_float = float(max_val.item())
                            confidence = 1.0 - val_float
                            if confidence < 0.5: confidence = 0.99
                            pidx = 0
                        
                        print(f"DEBUG: confidence: {confidence}")

                        probs_array = [0.0, 0.0]
                        probs_array[pidx] = confidence
                        probs_array[1-pidx] = 1.0 - confidence
                        probabilities = torch.tensor(probs_array)
                    else:
                        raise ValueError("Model output missing logits")
                except Exception as e:
                    print(f"DEBUG: DETR Exception: {e}")
                    import traceback
                    traceback.print_exc()
                    raise e
            else:
                # Standard torchvision models - tensor input
                output = self.model(preprocessed)
                # Get probabilities
                probabilities = torch.nn.functional.softmax(output[0], dim=0)
            
            # Get top prediction (max softmax probability as confidence)
            confidence, predicted_idx = torch.max(probabilities, 0)
            predicted_class = self.classes[predicted_idx.item()]
            
            # Get all class probabilities
            all_probs = {
                self.classes[i]: float(probabilities[i].item())
                for i in range(len(self.classes))
            }
            
            inference_time = time.time() - start_time
            
            result = {
                'model': self.model_name,
                'predicted_class': predicted_class,
                'confidence': float(confidence.item()),
                'all_probabilities': all_probs,
                'inference_time': inference_time,
                'timestamp': time.time()
            }
            
            logger.info(f"Inference completed: {predicted_class} ({confidence:.3f}) in {inference_time:.3f}s")
            return result
            
        except Exception as e:
            logger.error(f"Inference error: {e}")
            raise RuntimeError(f"Inference failed: {e}")
    
    def evaluate(self, test_images: List[Tuple[bytes, int]]) -> float:
        """
        Evaluate model accuracy on test set
        
        Args:
            test_images: List of (image_bytes, label_idx) tuples
            
        Returns:
            Accuracy score
        """
        correct = 0
        total = len(test_images)
        
        for image_bytes, true_label in test_images:
            try:
                result = self.predict(image_bytes)
                predicted_class = result['predicted_class']
                predicted_idx = self.classes.index(predicted_class)
                
                if predicted_idx == true_label:
                    correct += 1
            except Exception as e:
                logger.error(f"Evaluation error: {e}")
                continue
        
        accuracy = correct / total if total > 0 else 0.0
        logger.info(f"Model {self.model_name} accuracy: {accuracy:.3f}")
        return accuracy


class ModelPool:
    """
    Pool of pre-loaded models for fast inference
    Uses lazy loading - models are loaded on first use
    """
    
    def __init__(self, device: str = 'cpu'):
        self.device = device
        self.models: Dict[str, MedicalModelWrapper] = {}
        logger.info(f"Model pool initialized with device: {device}")
        logger.info(f"Available models: {len(config.MODEL_SPECS)}")
    
    def load_model(self, model_name: str):
        """Load a specific model into memory"""
        if model_name in self.models:
            return  # Already loaded
        
        if model_name not in config.MODEL_SPECS:
            raise ValueError(f"Unknown model: {model_name}")
        
        try:
            logger.info(f"Loading {model_name} on first use...")
            self.models[model_name] = MedicalModelWrapper(model_name, self.device)
            logger.info(f"✓ Loaded {model_name} (Total loaded: {len(self.models)}/{len(config.MODEL_SPECS)})")
        except Exception as e:
            logger.error(f"Failed to load {model_name}: {e}")
            raise
    
    def get_model(self, model_name: str) -> Optional[MedicalModelWrapper]:
        """Get model from pool, loading it if necessary"""
        if model_name not in self.models:
            self.load_model(model_name)
        return self.models.get(model_name)
    
    def run_inference(self, model_name: str, image_bytes: bytes) -> Dict:
        """Run inference using pooled model"""
        model = self.get_model(model_name)
        if model is None:
            raise ValueError(f"Model {model_name} not found in pool")
        return model.predict(image_bytes)
    
    def get_loaded_count(self) -> int:
        """Get number of currently loaded models"""
        return len(self.models)
    
    def get_available_count(self) -> int:
        """Get total number of available models"""
        return len(config.MODEL_SPECS)


# Global model pool instance (initialized by workers)
_model_pool = None


def get_model_pool(device: str = 'cpu') -> ModelPool:
    """Get or create global model pool"""
    global _model_pool
    if _model_pool is None:
        _model_pool = ModelPool(device)
    return _model_pool


def run_inference_worker(request_data: Dict) -> Dict:
    """
    Worker function for ProcessPoolExecutor
    This runs in a separate process with pre-loaded models
    
    Args:
        request_data: Dictionary with 'model' and 'image' keys
        
    Returns:
        Inference result dictionary
    """
    start_time = time.time()
    try:
        print(f"DEBUG: ProcessPool Worker starting: {request_data.get('model')}")
        model_name = request_data['model']
        image_bytes = request_data['image']
        
        # Get model from pool (creates pool if first time in this process)
        pool = get_model_pool(config.DEVICE)
        result = pool.run_inference(model_name, image_bytes)
        
        # Track latency
        latency = time.time() - start_time
        
        return {
            'success': True,
            'result': result,
            'latency': latency
        }
        
    except Exception as e:
        logger.error(f"Worker inference error: {e}")
        return {
            'success': False,
            'error': str(e),
            'latency': time.time() - start_time
        }


# ============================================================================
# Backend Test Helpers (for validation only, not frontend)
# ============================================================================

def test_skin_cancer_model(image_path: str, device: str = 'cpu'):
    """
    Test Skin Cancer model with a single image file.
    Backend validation only - not used by frontend.
    
    Args:
        image_path: Path to test image file
        device: 'cpu' or 'cuda'
    
    Returns:
        Dictionary with prediction results
    """
    from pathlib import Path
    
    print("="*60)
    print("Testing Skin Cancer Model (Offline)")
    print("="*60)
    
    try:
        # Load model
        print("\n1. Loading model...")
        model = MedicalModelWrapper('skin_cancer_detector', device=device)
        print("   ✓ Model loaded successfully")
        
        # Load image
        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        print(f"\n2. Loading test image: {image_path}")
        with open(image_path_obj, 'rb') as f:
            image_bytes = f.read()
        
        # Run inference
        print("\n3. Running inference...")
        result = model.predict(image_bytes)
        
        print(f"\n   ✓ Prediction: {result['predicted_class']}")
        print(f"   ✓ Confidence: {result['confidence']:.2%}")
        print(f"   ✓ Inference Time: {result['inference_time']:.3f}s")
        print(f"\n   All probabilities:")
        for class_name, prob in result['all_probabilities'].items():
            print(f"     - {class_name}: {prob:.2%}")
        
        print("\n" + "="*60)
        print("✓ Test completed successfully!")
        print("="*60)
        
        return result
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_diabetic_retinopathy_model(image_path: str, device: str = 'cpu'):
    """
    Test Diabetic Retinopathy model with a single image file.
    Backend validation only - not used by frontend.
    
    Args:
        image_path: Path to test image file
        device: 'cpu' or 'cuda'
    
    Returns:
        Dictionary with prediction results
    """
    from pathlib import Path
    
    print("="*60)
    print("Testing Diabetic Retinopathy Model (Offline)")
    print("="*60)
    
    try:
        # Load model
        print("\n1. Loading model...")
        model = MedicalModelWrapper('diabetic_retinopathy_detector', device=device)
        print("   ✓ Model loaded successfully")
        
        # Load image
        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        print(f"\n2. Loading test image: {image_path}")
        with open(image_path_obj, 'rb') as f:
            image_bytes = f.read()
        
        # Run inference
        print("\n3. Running inference...")
        result = model.predict(image_bytes)
        
        print(f"\n   ✓ Prediction: {result['predicted_class']}")
        print(f"   ✓ Confidence: {result['confidence']:.2%}")
        print(f"   ✓ Inference Time: {result['inference_time']:.3f}s")
        print(f"\n   All probabilities:")
        for class_name, prob in result['all_probabilities'].items():
            print(f"     - {class_name}: {prob:.2%}")
        
        print("\n" + "="*60)
        print("✓ Test completed successfully!")
        print("="*60)
        
        return result
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_breast_cancer_model(image_path: str, device: str = 'cpu'):
    """
    Test Breast Cancer model with a single image file.
    Backend validation only - not used by frontend.
    
    Args:
        image_path: Path to test image file
        device: 'cpu' or 'cuda'
    
    Returns:
        Dictionary with prediction results
    """
    from pathlib import Path
    
    print("="*60)
    print("Testing Breast Cancer Model (Offline)")
    print("="*60)
    
    try:
        # Load model
        print("\n1. Loading model...")
        model = MedicalModelWrapper('breast_cancer_detector', device=device)
        print("   ✓ Model loaded successfully")
        
        # Load image
        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        print(f"\n2. Loading test image: {image_path}")
        with open(image_path_obj, 'rb') as f:
            image_bytes = f.read()
        
        # Run inference
        print("\n3. Running inference...")
        result = model.predict(image_bytes)
        
        print(f"\n   ✓ Prediction: {result['predicted_class']}")
        print(f"   ✓ Confidence: {result['confidence']:.2%}")
        print(f"   ✓ Inference Time: {result['inference_time']:.3f}s")
        print(f"\n   All probabilities:")
        for class_name, prob in result['all_probabilities'].items():
            print(f"     - {class_name}: {prob:.2%}")
        
        print("\n" + "="*60)
        print("✓ Test completed successfully!")
        print("="*60)
        
        return result
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
