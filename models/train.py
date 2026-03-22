"""
Model Training Pipeline
Fine-tune medical imaging models on specific datasets
"""

import os
import sys
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms, models
from pathlib import Path
from typing import Dict, Optional, Tuple
import time
from tqdm import tqdm
import json

sys.path.append(str(Path(__file__).parent.parent))
from config import MODEL_SPECS, BASE_DIR


class MedicalImageDataset(Dataset):
    """Generic medical image dataset loader"""
    
    def __init__(self, root_dir: str, transform=None, split='train'):
        """
        Args:
            root_dir: Root directory with subdirectories for each class
            transform: Optional transform to be applied on images
            split: 'train', 'val', or 'test'
        """
        self.root_dir = Path(root_dir) / split
        self.transform = transform
        self.samples = []
        self.class_to_idx = {}
        
        # Scan directories
        if self.root_dir.exists():
            self._scan_directory()
    
    def _scan_directory(self):
        """Scan directory structure for images and labels"""
        classes = sorted([d.name for d in self.root_dir.iterdir() if d.is_dir()])
        self.class_to_idx = {cls_name: i for i, cls_name in enumerate(classes)}
        
        for class_name in classes:
            class_dir = self.root_dir / class_name
            for img_path in class_dir.glob('*'):
                if img_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                    self.samples.append((str(img_path), self.class_to_idx[class_name]))
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        
        from PIL import Image
        image = Image.open(img_path).convert('RGB')
        
        if self.transform:
            image = self.transform(image)
        
        return image, label


class ModelTrainer:
    """Train and fine-tune medical imaging models"""
    
    def __init__(self, model_name: str, dataset_path: str, device: str = None):
        """
        Initialize trainer
        
        Args:
            model_name: Name of model from MODEL_SPECS
            dataset_path: Path to dataset directory
            device: Device to train on (cuda/cpu)
        """
        self.model_name = model_name
        self.dataset_path = Path(dataset_path)
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        
        if model_name not in MODEL_SPECS:
            raise ValueError(f"Unknown model: {model_name}")
        
        self.model_spec = MODEL_SPECS[model_name]
        self.num_classes = self.model_spec['num_classes']
        
        # Create weights directory
        self.weights_dir = Path(BASE_DIR) / "models" / "weights"
        self.weights_dir.mkdir(parents=True, exist_ok=True)
        
        # Training hyperparameters
        self.batch_size = 32
        self.num_epochs = 50
        self.learning_rate = 0.001
        self.weight_decay = 1e-4
        self.best_val_acc = 0.0
        
        print(f"Initializing trainer for {model_name}")
        print(f"Device: {self.device}")
        print(f"Dataset: {dataset_path}")
        print(f"Classes: {self.num_classes}")
    
    def _create_model(self) -> nn.Module:
        """Create model architecture"""
        arch_name = self.model_spec['architecture'].lower().replace('-', '')
        
        # Load pretrained model
        if arch_name.startswith('resnet'):
            if arch_name == 'resnet50':
                model = models.resnet50(pretrained=True)
            elif arch_name == 'resnet34':
                model = models.resnet34(pretrained=True)
            model.fc = nn.Linear(model.fc.in_features, self.num_classes)
            
        elif arch_name.startswith('densenet'):
            model = models.densenet121(pretrained=True)
            model.classifier = nn.Linear(model.classifier.in_features, self.num_classes)
            
        elif arch_name.startswith('mobilenet'):
            model = models.mobilenet_v2(pretrained=True)
            model.classifier[1] = nn.Linear(model.classifier[1].in_features, self.num_classes)
            
        elif arch_name.startswith('efficientnet'):
            model = models.efficientnet_b0(pretrained=True)
            model.classifier[1] = nn.Linear(model.classifier[1].in_features, self.num_classes)
            
        elif arch_name.startswith('vgg'):
            model = models.vgg19(pretrained=True)
            model.classifier[6] = nn.Linear(4096, self.num_classes)
            
        elif arch_name.startswith('inception'):
            model = models.inception_v3(pretrained=True)
            model.fc = nn.Linear(model.fc.in_features, self.num_classes)
        
        else:
            raise ValueError(f"Unsupported architecture: {arch_name}")
        
        return model.to(self.device)
    
    def _get_transforms(self) -> Tuple[transforms.Compose, transforms.Compose]:
        """Get training and validation transforms"""
        train_transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.RandomCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        val_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        return train_transform, val_transform
    
    def _create_dataloaders(self) -> Tuple[DataLoader, DataLoader]:
        """Create training and validation dataloaders"""
        train_transform, val_transform = self._get_transforms()
        
        train_dataset = MedicalImageDataset(
            str(self.dataset_path),
            transform=train_transform,
            split='train'
        )
        
        val_dataset = MedicalImageDataset(
            str(self.dataset_path),
            transform=val_transform,
            split='val'
        )
        
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=4,
            pin_memory=True if self.device == 'cuda' else False
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=4,
            pin_memory=True if self.device == 'cuda' else False
        )
        
        print(f"Training samples: {len(train_dataset)}")
        print(f"Validation samples: {len(val_dataset)}")
        
        return train_loader, val_loader
    
    def train_epoch(self, model: nn.Module, train_loader: DataLoader, 
                   criterion: nn.Module, optimizer: optim.Optimizer) -> Tuple[float, float]:
        """Train for one epoch"""
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        pbar = tqdm(train_loader, desc="Training")
        for inputs, labels in pbar:
            inputs, labels = inputs.to(self.device), labels.to(self.device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()
            
            # Update progress bar
            pbar.set_postfix({
                'loss': f'{running_loss/len(pbar):.3f}',
                'acc': f'{100.*correct/total:.2f}%'
            })
        
        epoch_loss = running_loss / len(train_loader)
        epoch_acc = 100. * correct / total
        
        return epoch_loss, epoch_acc
    
    def validate(self, model: nn.Module, val_loader: DataLoader, 
                criterion: nn.Module) -> Tuple[float, float]:
        """Validate model"""
        model.eval()
        running_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            pbar = tqdm(val_loader, desc="Validation")
            for inputs, labels in pbar:
                inputs, labels = inputs.to(self.device), labels.to(self.device)
                
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                
                running_loss += loss.item()
                _, predicted = outputs.max(1)
                total += labels.size(0)
                correct += predicted.eq(labels).sum().item()
                
                pbar.set_postfix({
                    'loss': f'{running_loss/len(pbar):.3f}',
                    'acc': f'{100.*correct/total:.2f}%'
                })
        
        epoch_loss = running_loss / len(val_loader)
        epoch_acc = 100. * correct / total
        
        return epoch_loss, epoch_acc
    
    def train(self):
        """Main training loop"""
        print("\n" + "="*60)
        print(f"Training {self.model_name}")
        print("="*60 + "\n")
        
        # Create model
        model = self._create_model()
        
        # Create dataloaders
        train_loader, val_loader = self._create_dataloaders()
        
        if len(train_loader) == 0:
            print("ERROR: No training data found!")
            print(f"Expected structure: {self.dataset_path}/train/<class_name>/*.jpg")
            return
        
        # Loss and optimizer
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=self.learning_rate, 
                              weight_decay=self.weight_decay)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', 
                                                         factor=0.5, patience=5)
        
        # Training history
        history = {
            'train_loss': [],
            'train_acc': [],
            'val_loss': [],
            'val_acc': []
        }
        
        # Training loop
        start_time = time.time()
        
        for epoch in range(self.num_epochs):
            print(f"\nEpoch {epoch+1}/{self.num_epochs}")
            print("-" * 60)
            
            # Train
            train_loss, train_acc = self.train_epoch(model, train_loader, criterion, optimizer)
            
            # Validate
            val_loss, val_acc = self.validate(model, val_loader, criterion)
            
            # Update scheduler
            scheduler.step(val_acc)
            
            # Save history
            history['train_loss'].append(train_loss)
            history['train_acc'].append(train_acc)
            history['val_loss'].append(val_loss)
            history['val_acc'].append(val_acc)
            
            print(f"\nEpoch {epoch+1} Summary:")
            print(f"  Train Loss: {train_loss:.4f}  Train Acc: {train_acc:.2f}%")
            print(f"  Val Loss:   {val_loss:.4f}  Val Acc:   {val_acc:.2f}%")
            
            # Save best model
            if val_acc > self.best_val_acc:
                self.best_val_acc = val_acc
                self._save_checkpoint(model, epoch, val_acc, history)
                print(f"  ✓ New best model saved! (Val Acc: {val_acc:.2f}%)")
        
        training_time = time.time() - start_time
        
        print("\n" + "="*60)
        print("Training Complete!")
        print(f"Best Validation Accuracy: {self.best_val_acc:.2f}%")
        print(f"Total Training Time: {training_time/60:.2f} minutes")
        print("="*60)
    
    def _save_checkpoint(self, model: nn.Module, epoch: int, 
                        val_acc: float, history: Dict):
        """Save model checkpoint"""
        checkpoint_path = self.weights_dir / f"{self.model_name}.pth"
        
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'val_acc': val_acc,
            'num_classes': self.num_classes,
            'architecture': self.model_spec['architecture'],
            'history': history
        }
        
        torch.save(checkpoint, checkpoint_path)
        
        # Save metadata
        metadata_path = self.weights_dir / f"{self.model_name}_metadata.json"
        metadata = {
            'model_name': self.model_name,
            'architecture': self.model_spec['architecture'],
            'num_classes': self.num_classes,
            'class_names': self.model_spec['classes'],
            'best_val_acc': val_acc,
            'epoch': epoch,
            'training_date': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Train medical imaging models")
    parser.add_argument(
        '--model',
        type=str,
        required=True,
        help='Model name from config.py',
        choices=list(MODEL_SPECS.keys())
    )
    parser.add_argument(
        '--dataset',
        type=str,
        required=True,
        help='Path to dataset directory'
    )
    parser.add_argument(
        '--epochs',
        type=int,
        default=50,
        help='Number of training epochs (default: 50)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size (default: 32)'
    )
    parser.add_argument(
        '--lr',
        type=float,
        default=0.001,
        help='Learning rate (default: 0.001)'
    )
    
    args = parser.parse_args()
    
    # Create trainer
    trainer = ModelTrainer(args.model, args.dataset)
    trainer.num_epochs = args.epochs
    trainer.batch_size = args.batch_size
    trainer.learning_rate = args.lr
    
    # Train
    trainer.train()


if __name__ == "__main__":
    main()
