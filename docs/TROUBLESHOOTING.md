# 🔧 Troubleshooting Guide - Medical AI Inference Server

**Version**: 2.0  
**Last Updated**: January 18, 2026

---

## Table of Contents

1. [Server Issues](#server-issues)
2. [Authentication Problems](#authentication-problems)
3. [Inference Failures](#inference-failures)
4. [Database Issues](#database-issues)
5. [Performance Problems](#performance-problems)
6. [Model Issues](#model-issues)
7. [Backup & Recovery](#backup--recovery)
8. [Network & Connectivity](#network--connectivity)
9. [Common Error Messages](#common-error-messages)
10. [Getting Help](#getting-help)

---

## Server Issues

### Server Won't Start

**Symptom**: `python main.py` fails or exits immediately

**Check 1: Port Already in Use**
```bash
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000
```

**Solution**:
```bash
# Option A: Kill process using port
taskkill /PID <PID> /F  # Windows
kill -9 <PID>  # Linux/Mac

# Option B: Change port in .env
PORT=8001
```

---

**Check 2: Python Version**
```bash
python --version
# Required: 3.8 - 3.12
```

**Solution**:
```bash
# Install correct Python version
# Windows: Download from python.org
# Ubuntu: sudo apt install python3.10
# Mac: brew install python@3.10
```

---

**Check 3: Dependencies Missing**
```bash
pip list | grep torch
pip list | grep fastapi
```

**Solution**:
```bash
pip install -r requirements.txt
```

---

**Check 4: Environment Variables**
```bash
# Check .env file exists
cat .env  # Linux/Mac
type .env  # Windows

# Required variables:
# API_SECRET_KEY
# JWT_SECRET_KEY
# DATABASE_URL
```

**Solution**:
```bash
# Run installer to generate
python install.py

# Or copy from example
cp .env.example .env
```

---

### Server Crashes During Startup

**Check Logs**:
```bash
tail -50 logs/server.log
tail -50 logs/error.log
```

**Common Causes**:

1. **Database Connection Failed**
```
Error: unable to open database file
```

**Solution**:
```bash
# Check database file exists
ls labeled_data.db

# Initialize database
python -c "from database.migrations import initialize_database; initialize_database()"
```

2. **Model Files Missing**
```
Error: [Errno 2] No such file or directory: 'models/weights/...'
```

**Solution**:
```bash
# Check model directory
ls models/weights/

# Download models
python download_additional_models.py
```

3. **GPU/CUDA Error**
```
RuntimeError: CUDA out of memory
```

**Solution**:
```bash
# Use CPU instead (edit .env)
DEVICE=cpu

# Or reduce batch size
BATCH_SIZE=1
```

---

### Server Randomly Crashes

**Check System Resources**:
```bash
# Windows
Task Manager → Performance

# Linux
htop
free -h
df -h
```

**Common Causes**:

1. **Out of Memory**
```bash
# Check memory usage
python -c "import psutil; print(f'RAM: {psutil.virtual_memory().percent}%')"
```

**Solution**:
```bash
# Reduce workers (.env)
WORKERS=2
PROCESS_POOL_WORKERS=4

# Enable memory limits
MAX_MEMORY_GB=8
```

2. **Disk Full**
```bash
df -h  # Linux/Mac
wmic logicaldisk get size,freespace,caption  # Windows
```

**Solution**:
```bash
# Clean old logs
find logs/ -name "*.log" -mtime +30 -delete

# Clean old backups
find backups/ -name "*.tar.gz" -mtime +60 -delete

# Clear cache
rm -rf __pycache__
rm -rf .pytest_cache
```

3. **Too Many Requests**
```
Error: Too many open files
```

**Solution** (Linux):
```bash
# Increase file descriptor limit
ulimit -n 4096

# Make permanent (edit /etc/security/limits.conf)
*  soft  nofile  4096
*  hard  nofile  8192
```

---

## Authentication Problems

### Cannot Login - Invalid Credentials

**Symptom**: `401 Unauthorized` or "Invalid credentials"

**Check 1: Username/Password Correct**
```python
# Test credentials manually
from api.user_management import get_user_manager

user_mgr = get_user_manager()
user = user_mgr.authenticate("hospital_001", "your_password")
if user:
    print("✓ Credentials valid")
else:
    print("✗ Invalid credentials")
```

---

**Check 2: Account Locked**
```python
# Check lock status
conn = user_mgr.get_connection()
cursor = conn.cursor()
cursor.execute("""
    SELECT username, failed_login_attempts, locked_until
    FROM users
    WHERE hospital_id = ?
""", ("hospital_001",))
print(cursor.fetchone())
```

**Solution**:
```python
# Unlock account
cursor.execute("""
    UPDATE users 
    SET locked_until = NULL, failed_login_attempts = 0
    WHERE hospital_id = ?
""", ("hospital_001",))
conn.commit()
print("✓ Account unlocked")
```

---

**Check 3: User Exists**
```python
user = user_mgr.get_user_by_hospital_id("hospital_001")
if not user:
    print("✗ User not found")
```

**Solution**:
```python
# Create user
from api.user_management import UserCreate

user_mgr.create_user(UserCreate(
    username="hospital_001",
    email="hospital@example.com",
    password="NewPass123!",
    role="radiologist",
    hospital_id="hospital_001"
))
```

---

### Token Expired

**Symptom**: `401 Unauthorized` or "Token expired"

**Solution**: Login again to get new token
```python
# Tokens expire after 1 hour (default)
# Frontend should refresh before expiration
```

**Increase Token Lifetime** (not recommended):
```bash
# Edit .env
JWT_EXPIRATION_MINUTES=120  # 2 hours
```

---

### Insufficient Permissions

**Symptom**: `403 Forbidden` or "Insufficient permissions"

**Check User Role**:
```python
user = user_mgr.get_user_by_id(user_id)
print(f"Role: {user['role']}")
```

**Role Permissions**:
- `admin`: Can do everything
- `radiologist`: Can review cases, cannot manage users
- `hospital_admin`: Can manage users in their hospital
- `viewer`: Read-only

**Solution**: Contact admin to change role
```python
# Admin changes user role
user_mgr.update_user(user_id, {"role": "radiologist"})
```

---

## Inference Failures

### Model Not Found

**Symptom**: `404 Not Found` or "Model pneumonia_detector not found"

**Check Models**:
```python
from api.model_manager import get_model_manager

model_mgr = get_model_manager()
models = model_mgr.list_models()
print("Available models:")
for model in models:
    print(f"  - {model['model_name']}")
```

**Solution**:
```bash
# Download models
python download_additional_models.py

# Check files exist
ls models/weights/
```

---

### Inference Timeout

**Symptom**: Request hangs or "Inference timeout"

**Check 1: GPU/CPU Usage**
```bash
# GPU
nvidia-smi

# CPU
top  # Linux/Mac
taskmgr  # Windows
```

**Solution**:
```bash
# Reduce image size (edit config.py)
IMAGE_SIZE = (224, 224)  # Instead of (512, 512)

# Increase timeout (.env)
INFERENCE_TIMEOUT_SECONDS=30
```

---

**Check 2: Model Loading**
```python
# Test model loading manually
import torch
from pathlib import Path

model_path = Path("models/weights/pneumonia_detector.pth")
try:
    checkpoint = torch.load(model_path, map_location='cpu')
    print("✓ Model loads successfully")
except Exception as e:
    print(f"✗ Model loading failed: {e}")
```

---

### Wrong Predictions

**Symptom**: Model predictions don't make sense

**Check 1: Image Quality**
```python
from PIL import Image

img = Image.open("chest_xray.jpg")
print(f"Size: {img.size}")
print(f"Mode: {img.mode}")  # Should be RGB or L

# Check if corrupted
try:
    img.verify()
    print("✓ Image OK")
except:
    print("✗ Image corrupted")
```

---

**Check 2: Model Version**
```python
model_info = model_mgr.get_model_info("pneumonia_detector")
print(f"Version: {model_info['version']}")
print(f"Accuracy: {model_info['accuracy']}")
```

**Solution**: Update model
```bash
# Download latest model
python download_additional_models.py --model pneumonia_detector
```

---

**Check 3: Preprocessing**
```python
# Verify image preprocessing
from models.model_loader import preprocess_image

img_tensor = preprocess_image(img_path)
print(f"Tensor shape: {img_tensor.shape}")  # Should be [1, 3, 224, 224]
print(f"Tensor range: [{img_tensor.min():.2f}, {img_tensor.max():.2f}]")
# Should be normalized: [0, 1] or [-1, 1]
```

---

## Database Issues

### Database Locked

**Symptom**: `database is locked`

**Cause**: SQLite doesn't support concurrent writes

**Solution 1: Reduce Concurrency**
```bash
# Edit .env
WORKERS=1  # Single worker for SQLite
```

**Solution 2: Migrate to PostgreSQL**
```python
from database.migrations import DatabaseMigrator

migrator = DatabaseMigrator()
migrator.migrate_sqlite_to_postgres(
    "postgresql://user:pass@localhost/medical_ai"
)
```

---

### Database Corrupted

**Symptom**: `database disk image is malformed`

**Check Integrity**:
```bash
sqlite3 labeled_data.db "PRAGMA integrity_check;"
```

**Solution 1: Restore from Backup**
```python
from api.backup_manager import get_backup_manager

backup_mgr = get_backup_manager()
backups = backup_mgr.list_backups()
print("Available backups:")
for b in backups:
    print(f"  {b['filename']} - {b['created_at']}")

# Restore latest
backup_mgr.restore_backup(backups[0]['filename'], restore_type="database")
```

**Solution 2: Repair Database**
```bash
# Dump and restore
sqlite3 labeled_data.db .dump > backup.sql
rm labeled_data.db
sqlite3 labeled_data.db < backup.sql
```

---

### Missing Tables

**Symptom**: `no such table: labeled_data`

**Solution**: Run migrations
```python
from database.migrations import initialize_database

initialize_database()
```

---

## Performance Problems

### Slow Inference

**Symptom**: Inference takes >5 seconds

**Check 1: Device (GPU vs CPU)**
```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"Device: {torch.cuda.get_device_name(0)}")
```

**Solution**: Enable GPU
```bash
# Edit .env
DEVICE=cuda

# Check CUDA installation
python -c "import torch; print(torch.version.cuda)"
```

---

**Check 2: Model Size**
```bash
ls -lh models/weights/
# Large models (>1GB) are slower
```

**Solution**: Use optimized models
```bash
# Download quantized models (smaller, faster)
python download_additional_models.py --quantized
```

---

**Check 3: Image Size**
```python
# Check image preprocessing size
from config import IMAGE_SIZE
print(f"Image size: {IMAGE_SIZE}")

# Reduce if too large
# Edit config.py
IMAGE_SIZE = (224, 224)  # Instead of (512, 512)
```

---

### High Memory Usage

**Symptom**: Server uses >10 GB RAM

**Check Memory**:
```python
import psutil
process = psutil.Process()
print(f"Memory: {process.memory_info().rss / 1e9:.1f} GB")
```

**Solution 1: Reduce Workers**
```bash
# Edit .env
WORKERS=2
PROCESS_POOL_WORKERS=4
```

**Solution 2: Clear Cache**
```python
import torch
torch.cuda.empty_cache()  # Clear GPU cache
```

**Solution 3: Use Model Checkpointing**
```bash
# Edit config.py
LOAD_MODELS_ON_DEMAND=True  # Don't preload all models
```

---

### Dashboard Slow to Load

**Check 1: Too Many Pending Reviews**
```python
conn = sqlite3.connect('labeled_data.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM labeled_data WHERE radiologist_label IS NULL")
count = cursor.fetchone()[0]
print(f"Pending reviews: {count}")
```

**Solution**: Limit query
```python
# Frontend should paginate
# GET /radiologist/pending-reviews?limit=50
```

---

**Check 2: Large Images**
```bash
# Check image sizes
find dataset_images/ -name "*.jpg" -size +5M
```

**Solution**: Create thumbnails
```python
from PIL import Image

for img_path in large_images:
    img = Image.open(img_path)
    img.thumbnail((800, 800))
    img.save(f"thumbnails/{img_path.name}")
```

---

## Model Issues

### Model Failed Validation

**Symptom**: Uploaded model rejected

**Check Validation Report**:
```python
from models.model_validator import ModelValidator

validator = ModelValidator()
passed, results = validator.validate_model(
    Path("models/weights/my_model.pth"),
    "my_model"
)

print(f"Passed: {passed}")
for test_name, test_result in results['tests'].items():
    print(f"{test_name}: {test_result['passed']}")
```

**Common Failures**:

1. **File Too Large**
```
format: {'passed': False, 'size_mb': 623.4}
```
**Solution**: Quantize model
```python
import torch

model = torch.load("model.pth")
quantized_model = torch.quantization.quantize_dynamic(
    model, {torch.nn.Linear}, dtype=torch.qint8
)
torch.save(quantized_model.state_dict(), "model_quantized.pth")
```

2. **Too Slow**
```
speed: {'passed': False, 'avg_time_seconds': 8.34}
```
**Solution**: Optimize model or use GPU

3. **Low Accuracy**
```
accuracy: {'passed': False, 'accuracy': 0.62}
```
**Solution**: Retrain model with more data

---

### Model Not Improving

**Symptom**: Accuracy stuck or decreasing

**Check Training Data**:
```python
# Check label distribution
cursor.execute("""
    SELECT radiologist_label, COUNT(*) 
    FROM labeled_data 
    WHERE radiologist_label IS NOT NULL
    GROUP BY radiologist_label
""")
print("Label distribution:")
for label, count in cursor.fetchall():
    print(f"  {label}: {count}")
```

**Solution**: Balance dataset
```python
# Need roughly equal samples per class
# If imbalanced, collect more data for minority class
```

---

**Check Radiologist Agreement**:
```python
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN model_prediction = radiologist_label THEN 1 ELSE 0 END) as agreed
    FROM labeled_data
    WHERE radiologist_label IS NOT NULL
""")
total, agreed = cursor.fetchone()
print(f"Agreement rate: {agreed/total:.1%}")
```

**If low agreement (<50%)**:
- Model might be fundamentally flawed
- Retrain from scratch
- Check preprocessing

---

## Backup & Recovery

### Backup Failed

**Check Disk Space**:
```bash
df -h  # Linux/Mac
wmic logicaldisk get size,freespace  # Windows
```

**Check Permissions**:
```bash
ls -la backups/  # Should be writable
```

**Solution**:
```bash
# Create backup directory
mkdir -p backups
chmod 755 backups

# Manual backup
python -c "from api.backup_manager import get_backup_manager; \
           get_backup_manager().create_backup('full')"
```

---

### Restore Failed

**Check Backup File**:
```bash
# Verify tar.gz file
tar -tzf backups/backup_full_20251123_143025.tar.gz | head

# Extract manually
tar -xzf backups/backup_full_20251123_143025.tar.gz -C /tmp/restore_test/
```

**Solution**:
```python
# Restore with error details
from api.backup_manager import get_backup_manager

backup_mgr = get_backup_manager()
try:
    backup_mgr.restore_backup("backup_full_20251123_143025.tar.gz", "full")
except Exception as e:
    print(f"Restore failed: {e}")
    import traceback
    traceback.print_exc()
```

---

## Network & Connectivity

### Cannot Access Dashboard

**Symptom**: Browser shows "Can't reach this page"

**Check 1: Server Running**
```bash
ps aux | grep python  # Linux/Mac
tasklist | findstr python  # Windows
```

**Solution**: Start server
```bash
start_server.bat
```

---

**Check 2: Firewall**
```bash
# Windows
netsh advfirewall firewall add rule name="Medical AI Server" dir=in action=allow protocol=TCP localport=8000

# Linux (ufw)
sudo ufw allow 8000/tcp

# Linux (firewalld)
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

---

**Check 3: Correct URL**
```
Correct: http://localhost:8000 or http://192.168.1.100:8000
Wrong: https://localhost:8000 (https not enabled by default)
```

---

### Slow Network Requests

**Check Network Latency**:
```bash
# Test from client machine
curl -w "Time: %{time_total}s\n" http://localhost:8000/health
```

**If >1 second**:
- Check server load (CPU/memory)
- Check network (ping server)
- Check database performance

---

## Common Error Messages

### "CUDA out of memory"

**Cause**: GPU memory exhausted

**Solutions**:
1. Use CPU: `DEVICE=cpu` in .env
2. Reduce batch size: `BATCH_SIZE=1`
3. Clear GPU cache:
```python
import torch
torch.cuda.empty_cache()
```
4. Restart server

---

### "No module named 'xxx'"

**Cause**: Missing dependency

**Solution**:
```bash
pip install xxx
# Or reinstall all dependencies
pip install -r requirements.txt
```

---

### "Permission denied"

**Cause**: Insufficient file permissions

**Solution** (Linux/Mac):
```bash
chmod 755 install.py
chmod -R 755 models/
chmod -R 755 logs/
chmod -R 755 backups/
```

**Solution** (Windows):
- Run as Administrator

---

### "Connection refused"

**Cause**: Server not running or wrong port

**Solutions**:
1. Check server running: `ps aux | grep python`
2. Check port: `netstat -an | grep 8000`
3. Check firewall
4. Check URL (http not https)

---

## Getting Help

### Collect Diagnostic Information

```bash
# System info
python --version
pip list

# Server logs
tail -100 logs/server.log > diagnostic_logs.txt
tail -100 logs/error.log >> diagnostic_logs.txt

# Configuration (REMOVE PASSWORDS FIRST!)
cat .env >> diagnostic_info.txt

# Database info
python -c "
import sqlite3
conn = sqlite3.connect('labeled_data.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
print('Tables:', [r[0] for r in cursor.fetchall()])
" >> diagnostic_info.txt
```

---

### Contact Support

**Before Contacting Support**:
1. Check this troubleshooting guide
2. Check logs for error messages
3. Try restarting server
4. Search GitHub issues

**Support Channels**:
- Email: support@medical-ai.com
- GitHub Issues: github.com/yourusername/medical-ai-server/issues
- Emergency Hotline: +1-800-XXX-XXXX (24/7)

**Include in Support Request**:
1. Error message (exact text)
2. Steps to reproduce
3. Logs (last 100 lines)
4. System info (OS, Python version)
5. What you've already tried

---

**Document Version**: 2.0  
**Last Updated**: November 23, 2025  
**Next Review**: Quarterly
