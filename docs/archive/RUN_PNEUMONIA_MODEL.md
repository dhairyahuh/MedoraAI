# 🚀 Quick Start: Run Pneumonia Model

## TL;DR - Quick Commands

```bash
# 1. Navigate to project
cd /Users/dhairya/Desktop/MedoraAI

# 2. Create and activate venv
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# OR: .venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Verify weights file exists
ls -lh models/weights/pneumonia_vit.pth

# 5. Test the model
python test_pneumonia.py

# 6. Run full server
python main.py --no-ssl
```

---

## Detailed Steps

### Step 1: Setup Virtual Environment

```bash
# Create venv
python3 -m venv .venv

# Activate (macOS/Linux)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate
```

**Verify:** Prompt should show `(.venv)`

### Step 2: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Key packages installed:**
- `torch==2.1.0` - PyTorch
- `transformers==4.35.0` - Hugging Face Transformers (for ViT)
- `fastapi`, `uvicorn` - Web server
- All other dependencies

### Step 3: Verify Weights File

```bash
ls -lh models/weights/pneumonia_vit.pth
# Should show: ~327MB file
```

If missing:
```bash
cp model_pneumonia/medical-model-inference-test/weights/pneumonia_vit.pth models/weights/pneumonia_vit.pth
```

### Step 4: Quick Test

```bash
python test_pneumonia.py
```

**Expected output:**
```
============================================================
Testing Pneumonia Model (Offline)
============================================================

1. Loading model...
   ✓ Model loaded successfully
   ✓ Weights file found (327.0 MB)

2. Testing inference...
   ✓ Prediction: Normal (or Pneumonia)
   ✓ Confidence: 85.23%
   ✓ Inference Time: 0.456s

============================================================
✓ All tests passed! Pneumonia model is working.
============================================================
```

### Step 5: Run Full Server

```bash
python main.py --no-ssl
```

**Access:**
- API: http://localhost:8000
- Dashboard: http://localhost:8000/dashboard
- Docs: http://localhost:8000/docs

### Step 6: Test via API

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Submit prediction
curl -X POST "http://localhost:8000/api/v1/predict" \
  -H "X-API-Key: dev-key-12345" \
  -F "image=@path/to/chest_xray.jpg" \
  -F "disease_type=chest_xray"
```

---

## Troubleshooting

### "ERROR: Could not find a version that satisfies the requirement torch==2.1.0"
**Solution:** This happens with Python 3.13+. The requirements.txt has been updated to use compatible versions (torch>=2.8.0). Just run:
```bash
pip install -r requirements.txt
```

### "ModuleNotFoundError: No module named 'transformers'"
```bash
source .venv/bin/activate
pip install transformers>=4.35.0
```

### "FileNotFoundError: Pneumonia model weights not found"
```bash
# Check if file exists
ls models/weights/pneumonia_vit.pth

# Copy if missing
cp model_pneumonia/medical-model-inference-test/weights/pneumonia_vit.pth models/weights/pneumonia_vit.pth
```

### "Port 8000 already in use"
```bash
# Find process
lsof -i :8000  # macOS/Linux
# OR
netstat -ano | findstr :8000  # Windows

# Kill process or change port in config.py
```

---

## Verification Checklist

- [ ] Virtual environment created
- [ ] Dependencies installed (`pip list` shows transformers)
- [ ] Weights file exists (`models/weights/pneumonia_vit.pth`)
- [ ] Test script passes (`python test_pneumonia.py`)
- [ ] Server starts without errors
- [ ] API responds to health check

---

## Full Documentation

See `PNEUMONIA_MODEL_SETUP.md` for complete setup guide with troubleshooting.
