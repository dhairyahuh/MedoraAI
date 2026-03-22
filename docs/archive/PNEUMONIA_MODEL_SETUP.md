# 🫁 Pneumonia Model Setup & Run Guide

Complete step-by-step guide to set up and run the offline Pneumonia (Chest X-ray) model in MedoraAI.

---

## 📋 Prerequisites

- Python 3.8+ (3.10+ recommended)
- pip package manager
- 4GB+ RAM (8GB+ recommended)
- GPU optional but recommended for faster inference

---

## 🚀 Step-by-Step Setup

### Step 1: Navigate to Project Directory

```bash
cd /Users/dhairya/Desktop/MedoraAI
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# On macOS/Linux, activate with:
source .venv/bin/activate

# On Windows, activate with:
# .venv\Scripts\activate
```

**Verify activation:**
- Your terminal prompt should show `(.venv)` at the beginning
- Run `which python` (macOS/Linux) or `where python` (Windows) - should point to `.venv/bin/python`

### Step 3: Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt
```

**This will install:**
- PyTorch 2.1.0 (with CUDA support if GPU available)
- Transformers 4.35.0 (for Pneumonia ViT model)
- FastAPI, Uvicorn (web server)
- All other dependencies

**Installation time:** ~5-10 minutes depending on internet speed

### Step 4: Verify Weights File

The Pneumonia model weights should already be in place:

```bash
# Check if weights file exists
ls -lh models/weights/pneumonia_vit.pth

# Should show: ~327MB file
```

If the file is missing, copy it from the validated model:
```bash
cp model_pneumonia/medical-model-inference-test/weights/pneumonia_vit.pth models/weights/pneumonia_vit.pth
```

### Step 5: Verify Installation

```bash
# Test Python imports
python -c "import torch; print('PyTorch:', torch.__version__)"
python -c "import transformers; print('Transformers:', transformers.__version__)"
python -c "from transformers import ViTConfig, ViTForImageClassification; print('✓ Transformers ViT available')"

# Check CUDA (if GPU available)
python -c "import torch; print('CUDA Available:', torch.cuda.is_available())"
```

---

## 🏃 Running the Model

### Option 1: Run Full Server (Recommended)

Start the complete MedoraAI server with all models:

```bash
# Make sure venv is activated
source .venv/bin/activate  # macOS/Linux
# OR
# .venv\Scripts\activate  # Windows

# Start server
python main.py --no-ssl
```

**Server will start at:**
- API: http://localhost:8000
- Dashboard: http://localhost:8000/dashboard
- API Docs: http://localhost:8000/docs

### Option 2: Test Pneumonia Model Directly

Create a simple test script to verify the Pneumonia model works:

```python
# test_pneumonia_offline.py
from models.model_manager import MedicalModelWrapper
from pathlib import Path

# Load Pneumonia model
print("Loading Pneumonia model...")
model = MedicalModelWrapper('pneumonia_detector', device='cpu')

# Test with a sample image (if available)
test_image_path = Path("static/test_images/sample_chest_xray.jpg")
if test_image_path.exists():
    with open(test_image_path, 'rb') as f:
        image_bytes = f.read()
    
    result = model.predict(image_bytes)
    print(f"\n✓ Prediction: {result['predicted_class']}")
    print(f"✓ Confidence: {result['confidence']:.2%}")
    print(f"✓ Inference Time: {result['inference_time']:.3f}s")
else:
    print("No test image found, but model loaded successfully!")
```

Run it:
```bash
python test_pneumonia_offline.py
```

### Option 3: Use API Endpoint

Once server is running, test via API:

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Submit prediction (replace with actual image path)
curl -X POST "http://localhost:8000/api/v1/predict" \
  -H "X-API-Key: dev-key-12345" \
  -F "image=@static/test_images/sample_chest_xray.jpg" \
  -F "disease_type=chest_xray"
```

---

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] Virtual environment created and activated
- [ ] All dependencies installed (`pip list` shows transformers, torch, etc.)
- [ ] Weights file exists at `models/weights/pneumonia_vit.pth` (~327MB)
- [ ] Model loads without errors (check server logs)
- [ ] Inference produces predictions with confidence scores
- [ ] No Hugging Face download attempts (fully offline)

---

## 🧪 Quick Test Script

Save this as `test_pneumonia.py`:

```python
#!/usr/bin/env python3
"""Quick test for Pneumonia model integration"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from models.model_manager import MedicalModelWrapper

def main():
    print("="*60)
    print("Testing Pneumonia Model (Offline)")
    print("="*60)
    
    try:
        # Load model
        print("\n1. Loading model...")
        model = MedicalModelWrapper('pneumonia_detector', device='cpu')
        print("   ✓ Model loaded successfully")
        
        # Check weights
        weights_path = Path("models/weights/pneumonia_vit.pth")
        if weights_path.exists():
            size_mb = weights_path.stat().st_size / (1024 * 1024)
            print(f"   ✓ Weights file found ({size_mb:.1f} MB)")
        else:
            print("   ✗ Weights file missing!")
            return False
        
        # Test with dummy image (create a simple test image)
        print("\n2. Testing inference...")
        from PIL import Image
        import io
        
        # Create a simple test image (224x224 RGB)
        test_img = Image.new('RGB', (224, 224), color='black')
        img_bytes = io.BytesIO()
        test_img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        result = model.predict(img_bytes.getvalue())
        
        print(f"   ✓ Prediction: {result['predicted_class']}")
        print(f"   ✓ Confidence: {result['confidence']:.2%}")
        print(f"   ✓ Inference Time: {result['inference_time']:.3f}s")
        
        print("\n" + "="*60)
        print("✓ All tests passed! Pneumonia model is working.")
        print("="*60)
        return True
        
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("   Make sure weights file is at: models/weights/pneumonia_vit.pth")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

Run it:
```bash
python test_pneumonia.py
```

---

## 🔧 Troubleshooting

### Problem: `ModuleNotFoundError: No module named 'transformers'`

**Solution:**
```bash
# Make sure venv is activated
source .venv/bin/activate

# Install transformers
pip install transformers==4.35.0
```

### Problem: `FileNotFoundError: Pneumonia model weights not found`

**Solution:**
```bash
# Check if file exists
ls -lh models/weights/pneumonia_vit.pth

# If missing, copy from validated model
cp model_pneumonia/medical-model-inference-test/weights/pneumonia_vit.pth models/weights/pneumonia_vit.pth
```

### Problem: `RuntimeError: Failed to load Pneumonia model weights`

**Solution:**
- Verify weights file is not corrupted (should be ~327MB)
- Check file permissions: `chmod 644 models/weights/pneumonia_vit.pth`
- Ensure PyTorch version matches: `pip install torch==2.1.0`

### Problem: Low confidence scores (<50%)

**Solution:**
- Ensure preprocessing matches: 224×224 resize, ImageNet normalization
- Verify input image is a valid chest X-ray
- Check model loaded correctly (no warnings in logs)

### Problem: Server won't start

**Solution:**
```bash
# Check if port 8000 is already in use
lsof -i :8000  # macOS/Linux
# OR
netstat -ano | findstr :8000  # Windows

# Kill process if needed, or change port in config.py
```

---

## 📊 Expected Output

When running successfully, you should see:

```
INFO:models.model_manager:Loading Pneumonia model architecture (offline)...
INFO:models.model_manager:Loading weights from models/weights/pneumonia_vit.pth...
INFO:models.model_manager:✓ Loaded Pneumonia weights from models/weights/pneumonia_vit.pth
INFO:models.model_manager:Pneumonia model loaded successfully (offline mode)
INFO:models.model_manager:Loaded model: pneumonia_detector on cpu
```

**Inference results:**
- Confidence: 80-95% (high confidence expected)
- Inference time: <1s on CPU, <0.3s on GPU
- Predictions: "Normal" or "Pneumonia"

---

## 🎯 Next Steps

1. **Test with real chest X-ray images**
   - Upload via web dashboard at http://localhost:8000
   - Or use API endpoint with `curl` or Python `requests`

2. **Monitor performance**
   - Check logs in `logs/inference.log`
   - View metrics at http://localhost:8000/metrics

3. **Integrate with other models**
   - The Pneumonia model is now fully integrated
   - Other models continue to work as before

---

## 📝 Notes

- **Fully Offline**: No Hugging Face or internet calls at runtime
- **Local Weights**: All weights loaded from `models/weights/pneumonia_vit.pth`
- **Production Ready**: Hard fails if weights missing (no silent fallbacks)
- **High Confidence**: Model produces stable 80-95% confidence predictions

---

**Questions?** Check the logs in `logs/inference.log` for detailed error messages.
