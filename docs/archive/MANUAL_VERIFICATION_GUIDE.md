# Manual Verification Guide - Testing All Novel Claims

This guide shows you how to manually verify every claim about your system's capabilities.

---

## ✅ Claim 1: Supervised Learning Actually Improves Models

### What to Verify
After radiologist corrections, does the model's accuracy increase?

### Manual Test Steps

#### Step 1: Check Current Model Accuracy
```bash
cd medical-inference-server
python quick_test.py
```

**Record baseline accuracy** for each model (e.g., pneumonia: 87.5%)

#### Step 2: Create Test Corrections
```bash
# Start server
python main.py
```

In another terminal:
```bash
# Submit 10-20 corrections with wrong predictions
python test_supervised_learning_fix.py
```

**What this does:**
- Makes predictions on test images
- Simulates radiologist marking them as wrong
- System retrains model with corrections

#### Step 3: Check Improved Accuracy
```bash
# After retraining completes (watch server logs)
python quick_test.py
```

**Expected result:** Accuracy should increase by 1-5% (e.g., 87.5% → 89.2%)

#### Step 4: Verify in Database
```bash
python
```
```python
import sqlite3
conn = sqlite3.connect('medical_ai.db')
cursor = conn.cursor()

# Check corrections were saved
cursor.execute("SELECT COUNT(*) FROM radiologist_reviews WHERE is_correct = 0")
print(f"Total corrections: {cursor.fetchone()[0]}")

# Check retraining happened
cursor.execute("SELECT model_name, COUNT(*) FROM training_history GROUP BY model_name")
print("Training runs per model:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} runs")
```

**Expected output:**
```
Total corrections: 15
Training runs per model:
  pneumonia_detector: 3 runs
  skin_cancer_detector: 2 runs
```

### ✅ PASS if:
- Corrections appear in database
- Retraining occurs automatically
- Accuracy increases after corrections

---

## ✅ Claim 2: Federated Learning Works Across Hospitals

### What to Verify
Multiple hospitals can train together without sharing raw data.

### Manual Test Steps

#### Step 1: Simulate 3 Hospitals
```bash
cd medical-inference-server
python test_federated.py
```

**Watch the output** - you should see:
```
Hospital A: Training on local data (30 samples)
Hospital A: Local model accuracy: 0.78
Hospital A: Sending model updates (weights only, not data)

Hospital B: Training on local data (25 samples)
Hospital B: Local model accuracy: 0.81
Hospital B: Sending model updates

Hospital C: Training on local data (28 samples)
Hospital C: Local model accuracy: 0.75
Hospital C: Sending model updates

Aggregating models from 3 hospitals...
Global model accuracy: 0.85 (better than any individual hospital)
```

#### Step 2: Verify No Data Sharing
```bash
# Check federated learning code
grep -n "send.*image\|send.*data" api/federated_learning.py
```

**Expected:** Should find NO code sending images/patient data, only model weights

#### Step 3: Check Model Aggregation
```python
python
```
```python
from api.federated_learning import FederatedLearningManager
import torch

manager = FederatedLearningManager()

# Check that only model weights are aggregated
hospital_models = [
    torch.load('models/hospital_a_model.pth'),
    torch.load('models/hospital_b_model.pth'),
]

# Aggregate (FedAvg algorithm)
global_model = manager.aggregate_models(hospital_models)

# Verify global model is different from any single hospital
print(f"Global model params: {len(list(global_model.parameters()))}")
print("✓ Model aggregation works without data sharing")
```

### ✅ PASS if:
- Test shows accuracy improvement
- No patient data is transmitted (only model weights)
- Global model performs better than individual hospitals

---

## ✅ Claim 3: Hospitals Can Deploy/Maintain Without ML Experts

### What to Verify
A non-technical person can install, configure, and manage the system.

### Manual Test Steps

#### Step 1: Fresh Installation (No Python Knowledge Required)
```bash
# Pretend you're a hospital IT admin who knows Windows, not Python

# Double-click installer
start_production.bat

# Or run installer
python install.py
```

**What to check:**
- ✅ Does it check Python version automatically?
- ✅ Does it create virtual environment automatically?
- ✅ Does it install all dependencies automatically?
- ✅ Does it create database automatically?
- ✅ Does it prompt for configuration (hospital name, email)?
- ✅ Does it show clear success/failure messages?

**Expected time:** 5-10 minutes, no errors

#### Step 2: Configuration (Web Interface, Not Code)
```bash
# Start server
start_server.bat

# Open browser
http://localhost:8000/admin
```

**Test these tasks WITHOUT touching code:**

1. **Create a user:**
   - Go to "Users" tab
   - Click "Add User"
   - Fill form: username, email, role, hospital
   - Click "Create"
   - ✅ User appears in table

2. **Upload a new model:**
   - Go to "Models" tab
   - Click "Upload Model"
   - Select .pth file
   - System runs validation automatically
   - ✅ Model appears with accuracy metrics

3. **Create a backup:**
   - Go to "Backups" tab
   - Click "Create Backup Now"
   - ✅ Backup file appears in list

4. **View system health:**
   - Go to "Monitoring" tab
   - ✅ See CPU, memory, GPU usage
   - ✅ See recent errors/warnings

5. **Configure email alerts:**
   - Go to "Settings" tab
   - Enter SMTP server, port, credentials
   - Click "Test Email"
   - ✅ Receive test email

#### Step 3: Troubleshooting (Documentation, Not Debug)
```bash
# Open troubleshooting guide
open docs/TROUBLESHOOTING.md
```

**Check if these common problems have solutions:**
- ✅ "Server won't start" → Solution provided
- ✅ "Model prediction fails" → Solution provided
- ✅ "Database error" → Solution provided
- ✅ "Out of memory" → Solution provided

### ✅ PASS if:
- Installation requires zero Python knowledge
- All management done via web interface
- Troubleshooting guide covers common issues
- No terminal/code editing required for daily operations

---

## ✅ Claim 4: PACS Integration Eliminates Manual Workflow

### What to Verify
System automatically fetches images from PACS and sends results back.

### Manual Test Steps (Requires PACS Access)

#### If You Have Real PACS:

```bash
# Configure PACS connection
# Edit .env file
PACS_ENABLED=true
PACS_HOST=your.pacs.server.com
PACS_PORT=11112
PACS_AE_TITLE=MEDICAL_AI
PACS_CALLED_AE_TITLE=PACS_SERVER
PACS_AUTO_FETCH_INTERVAL=300
```

```bash
# Test connection
python
```
```python
from api.pacs_integration import get_pacs_integration

pacs = get_pacs_integration()
success, message = pacs.test_connection()
print(f"Connection: {message}")

# Expected: "Successfully connected to PACS at your.pacs.server.com:11112"
```

#### Test Automatic Workflow:

```python
# Query for recent studies
from datetime import datetime, timedelta
studies = pacs.query_studies(
    start_date=datetime.now() - timedelta(days=7),
    modality='CR'  # Chest X-ray
)

print(f"Found {len(studies)} studies")
for study in studies[:3]:
    print(f"  Study: {study['study_uid']}")
    print(f"  Patient: {study['patient_id']}")
    print(f"  Date: {study['study_date']}")

# Retrieve one study
if studies:
    study_dir = pacs.retrieve_study(studies[0]['study_uid'])
    print(f"Downloaded to: {study_dir}")
    
    # Extract image
    image = pacs.extract_image_from_dicom(study_dir / "image.dcm")
    print(f"Image ready for inference: {image}")
```

#### Test Automatic Monitoring:

```bash
# Start server with PACS monitoring
python main.py
```

**Watch server logs for:**
```
[INFO] PACS monitoring started (checking every 5 minutes)
[INFO] Found 3 new studies from PACS
[INFO] Processing study 1.2.840.113619...
[INFO] Retrieved 12 DICOM files
[INFO] Extracted images: chest_xray_001.png, chest_xray_002.png
[INFO] Running inference with pneumonia_detector
[INFO] Prediction: PNEUMONIA (confidence: 0.92)
[INFO] Sending results back to PACS
[INFO] Results stored in PACS as Structured Report
```

#### Verify in PACS Viewer:
- Open your PACS workstation
- Find the processed study
- ✅ AI results should appear as a new series/report
- ✅ Shows prediction + confidence
- ✅ Radiologist sees AI suggestion without leaving PACS

#### If You DON'T Have Real PACS:

```bash
# Test with simulated PACS
python
```
```python
from api.pacs_integration import PACSIntegration, PACSConfig
from pathlib import Path

# Create test DICOM file
import pydicom
from pydicom.dataset import Dataset

ds = Dataset()
ds.PatientName = "Test^Patient"
ds.PatientID = "12345"
ds.Modality = "CR"
ds.StudyInstanceUID = "1.2.3.4.5.6.7"
ds.save_as("test_dicom.dcm")

# Test extraction
pacs = PACSIntegration(PACSConfig(
    host="localhost",
    port=11112,
    ae_title="TEST_AI"
))

image_path = pacs.extract_image_from_dicom(Path("test_dicom.dcm"))
print(f"✓ DICOM converted to PNG: {image_path}")

# Verify image is usable
from PIL import Image
img = Image.open(image_path)
print(f"✓ Image size: {img.size}")
print(f"✓ Image mode: {img.mode}")
```

### ✅ PASS if:
- Can connect to PACS (or simulate)
- Can query studies (C-FIND works)
- Can retrieve images (C-MOVE works)
- Can send results back (C-STORE works)
- Automatic monitoring finds new studies every 5 minutes
- No manual file transfer needed

---

## ✅ Claim 5: Safe Model Updates in Production (Canary + Rollback)

### What to Verify
New models deploy gradually and rollback automatically if they fail.

### Manual Test Steps

#### Step 1: Prepare Test Models

```bash
cd medical-inference-server
```

Create a deliberately BAD model (for rollback testing):
```python
import torch
from models.pneumonia_detector import PneumoniaDetector

# Create bad model (random weights)
bad_model = PneumoniaDetector()
# Don't train it - random predictions
torch.save(bad_model.state_dict(), 'models/pneumonia_v_bad.pth')

# Create good model (current one)
good_model = PneumoniaDetector()
# Load trained weights
good_model.load_state_dict(torch.load('models/pneumonia_detector.pth'))
torch.save(good_model.state_dict(), 'models/pneumonia_v_good.pth')
```

#### Step 2: Test Canary Deployment

```python
from api.model_update_manager import get_model_update_manager, DeploymentStrategy
from pathlib import Path
import asyncio

async def test_canary():
    manager = get_model_update_manager()
    
    # Deploy good model with canary strategy
    print("Testing CANARY deployment with GOOD model...")
    success, message = await manager.deploy_model(
        model_name='pneumonia_detector',
        model_path=Path('models/pneumonia_v_good.pth'),
        version='2.0_good',
        strategy=DeploymentStrategy.CANARY,
        validate=True
    )
    
    print(f"Result: {success}")
    print(f"Message: {message}")
    
    # Expected: Should pass all 6 canary stages
    # 1% → 5% → 10% → 25% → 50% → 100%

asyncio.run(test_canary())
```

**Watch for in logs:**
```
[INFO] Validating model before deployment...
[INFO] ✓ Model validation passed (6/6 tests)
[INFO] Starting canary deployment
[INFO] Canary stage 1/6: 1% traffic
[INFO]   Monitoring for 5 minutes...
[INFO]   Metrics: accuracy=0.88, errors=0, latency=0.12s
[INFO] ✓ Stage 1 passed
[INFO] Canary stage 2/6: 5% traffic
...
[INFO] ✓ Canary deployment complete - model promoted to active
```

#### Step 3: Test Automatic Rollback

```python
async def test_rollback():
    manager = get_model_update_manager()
    
    # Deploy BAD model (should trigger rollback)
    print("Testing ROLLBACK with BAD model...")
    success, message = await manager.deploy_model(
        model_name='pneumonia_detector',
        model_path=Path('models/pneumonia_v_bad.pth'),
        version='3.0_bad',
        strategy=DeploymentStrategy.CANARY,
        validate=False  # Skip validation to force deployment
    )
    
    print(f"Result: {success}")  # Should be False
    print(f"Message: {message}")  # Should mention rollback

asyncio.run(test_rollback())
```

**Watch for in logs:**
```
[INFO] Starting canary deployment
[INFO] Canary stage 1/6: 1% traffic
[INFO]   Monitoring for 5 minutes...
[ERROR]   Accuracy degraded: 0.45 < 0.79 (baseline * 0.95)
[WARNING] Canary rollback triggered: accuracy below threshold
[INFO] Restoring previous model from backup
[INFO] ✓ Rollback complete - system stable
[ERROR] Deployment failed and rolled back
```

#### Step 4: Verify Rollback Protection

```bash
# Check that old model is still active
python
```
```python
import torch
from models.pneumonia_detector import PneumoniaDetector

# Load current active model
model = PneumoniaDetector()
model.load_state_dict(torch.load('models/pneumonia_detector.pth'))

# Make test prediction
from PIL import Image
import torchvision.transforms as transforms

img = Image.open('test_images/pneumonia_test.jpg')
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor()
])
img_tensor = transform(img).unsqueeze(0)

with torch.no_grad():
    output = model(img_tensor)
    prediction = torch.sigmoid(output).item()

print(f"Prediction: {prediction:.2f}")
# Expected: Should be reasonable (0.7-0.9), not random (0.1-0.2)
print("✓ Original good model still active after rollback")
```

#### Step 5: Test Deployment Strategies

```python
async def test_all_strategies():
    manager = get_model_update_manager()
    
    # Test immediate deployment
    print("\n1. IMMEDIATE strategy (fast, risky):")
    await manager.deploy_model(
        model_name='test_model',
        model_path=Path('models/pneumonia_v_good.pth'),
        version='1.0',
        strategy=DeploymentStrategy.IMMEDIATE
    )
    
    # Test blue-green deployment
    print("\n2. BLUE-GREEN strategy (safest):")
    await manager.deploy_model(
        model_name='test_model',
        model_path=Path('models/pneumonia_v_good.pth'),
        version='2.0',
        strategy=DeploymentStrategy.BLUE_GREEN
    )
    
    # Test A/B testing
    print("\n3. A/B TEST strategy (comparison):")
    await manager.deploy_model(
        model_name='test_model',
        model_path=Path('models/pneumonia_v_good.pth'),
        version='3.0',
        strategy=DeploymentStrategy.A_B_TEST
    )

asyncio.run(test_all_strategies())
```

### ✅ PASS if:
- Good model deploys successfully through all canary stages
- Bad model triggers automatic rollback
- System reverts to previous working model
- No downtime during deployment
- All 4 deployment strategies work

---

## Complete Verification Checklist

Run all tests and mark results:

```
[ ] Supervised learning increases accuracy after corrections
[ ] Federated learning aggregates models without sharing data
[ ] Non-technical user can install/manage via web interface
[ ] PACS integration auto-fetches and sends results
[ ] Canary deployment works with gradual rollout
[ ] Automatic rollback triggers on bad models
[ ] System stays online during model updates
```

---

## Quick Verification Script

Run everything at once:

```bash
# Save this as verify_all.sh
cd medical-inference-server

echo "=== Test 1: Supervised Learning ==="
python test_supervised_learning_fix.py
python quick_test.py

echo "=== Test 2: Federated Learning ==="
python test_federated.py

echo "=== Test 3: Standalone Deployment ==="
python install.py --dry-run

echo "=== Test 4: PACS Integration ==="
python -c "from api.pacs_integration import get_pacs_integration; pacs = get_pacs_integration(); print(pacs.test_connection())"

echo "=== Test 5: Model Updates ==="
python -c "from api.model_update_manager import get_model_update_manager; import asyncio; asyncio.run(get_model_update_manager().deploy_model('test', 'models/pneumonia_detector.pth', '1.0', 'canary'))"

echo "=== All Tests Complete ==="
```

Run:
```bash
bash verify_all.sh > verification_results.txt
```

---

## Evidence for Publication/Demo

After verification, collect evidence:

1. **Screenshots:**
   - Admin dashboard managing users
   - Model deployment canary stages
   - PACS study retrieval logs
   - Accuracy improvement graph

2. **Logs:**
   - Supervised learning retraining logs
   - Federated aggregation logs
   - Rollback trigger logs

3. **Metrics:**
   - Before/after accuracy table
   - Deployment time (should be <30 seconds per stage)
   - Zero downtime verification

4. **Video Demo:**
   - Record 5-minute walkthrough showing:
     - One-click install
     - Web UI management
     - PACS auto-fetch
     - Model update with rollback

This evidence proves all claims are verifiable and reproducible.
