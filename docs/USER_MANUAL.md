# 📘 Medical AI Inference Server - Complete User Manual

**Version**: 2.0  
**Date**: January 18, 2026  
**For**: Radiologists, Hospital IT, System Administrators

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [User Roles & Permissions](#user-roles--permissions)
4. [Radiologist Workflow](#radiologist-workflow)
5. [System Administration](#system-administration)
6. [Troubleshooting](#troubleshooting)
7. [Security & Compliance](#security--compliance)
8. [API Reference](#api-reference)

---

## Quick Start

### For Hospital IT (First Time Setup)

**Installation** (10 minutes):
```bash
# 1. Download system files
cd medical-inference-server

# 2. Run installer
python install.py

# 3. Follow prompts for configuration
#    - Server host: 0.0.0.0 (default)
#    - Port: 8000 (default)
#    - Database: SQLite (pilot) or PostgreSQL (production)
#    - Email alerts: Configure SMTP (optional)

# 4. Start server
start_server.bat   # Windows
./start_server.sh  # Linux/Mac
```

**Access System**:
- Radiologist Dashboard: http://localhost:8000/radiologist
- API Documentation: http://localhost:8000/docs
- Monitoring Dashboard: http://localhost:8000/monitoring/dashboard

**Default Admin Credentials** (displayed during install):
```
Username: admin
Password: <generated-password>
⚠️ CHANGE IMMEDIATELY AFTER FIRST LOGIN
```

---

### For Radiologists (Daily Use)

**Basic Workflow**:
1. **Login** → Open radiologist dashboard
2. **View Pending Reviews** → AI predictions waiting for confirmation
3. **Review Images** → Confirm or correct AI diagnosis
4. **Submit** → System learns from your feedback

**Time Investment**: 30-60 seconds per case

---

## Installation

### System Requirements

**Minimum** (Pilot Deployment):
- OS: Windows 10/11, Ubuntu 20.04+, macOS 11+
- CPU: 4 cores, 2.5 GHz
- RAM: 8 GB
- Disk: 50 GB free
- Python: 3.8 - 3.12
- Network: 10 Mbps

**Recommended** (Production):
- OS: Ubuntu 22.04 LTS Server
- CPU: 8 cores, 3.0 GHz (or GPU: NVIDIA GTX 1080+)
- RAM: 16 GB (32 GB with GPU)
- Disk: 500 GB SSD
- Python: 3.10+
- Network: 100 Mbps

---

### Installation Steps

#### Option 1: Automated Install (Recommended)

```bash
# Clone or download system
cd medical-inference-server

# Run installer
python install.py
```

**Installer Will**:
✅ Check Python version  
✅ Create virtual environment  
✅ Install all dependencies  
✅ Generate security keys  
✅ Create SSL certificates  
✅ Initialize database  
✅ Create admin account  
✅ Configure automatic backups  
✅ Setup monitoring alerts  

**Interactive Configuration**:
```
Server host [0.0.0.0]: <press Enter>
Server port [8000]: <press Enter>
Number of workers [4]: <press Enter>

Database type:
  1. SQLite (default, easy setup)
  2. PostgreSQL (production-ready)
Choose [1]: 1

Email Alerting (optional):
SMTP server (leave blank to skip): smtp.gmail.com
SMTP port [587]: 587
SMTP username: alerts@hospital.com
SMTP password: ********
Alert recipient email: admin@hospital.com

✓ Configuration complete!
```

**Output**:
```
================================================================================
Installation Complete!
================================================================================

📝 IMPORTANT CREDENTIALS:
   API Key: vK3mN8pL2qR9sT4wX7yZ1aB5cD9eF2gH
   Admin Password: uZ7yA5bC1dE6fG8hI3jK

⚠️  Save these credentials securely!

📋 NEXT STEPS:
1. Start server: start_server.bat
2. Access dashboard: http://localhost:8000/radiologist
3. Change admin password
4. Create radiologist accounts
================================================================================
```

---

#### Option 2: Manual Install

```bash
# 1. Create virtual environment
python -m venv .venv

# 2. Activate
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env with your settings

# 5. Initialize database
python -m database.migrations

# 6. Start server
python main.py
```

---

## User Roles & Permissions

### Role Overview

| Role | Use Case | Count | Permissions |
|------|----------|-------|-------------|
| **Admin** | System administrator | 1-2 | Full system access |
| **Radiologist** | Medical expert review | 5-50 | Review cases, train system |
| **Hospital Admin** | Department manager | 2-5 | Manage hospital users, view reports |
| **Viewer** | Read-only observer | Unlimited | View reviews, metrics |

---

### Admin

**Can Do**:
- ✅ Create/delete all users
- ✅ Upload/delete models
- ✅ Configure system settings
- ✅ Access all hospitals' data
- ✅ Manage backups
- ✅ View audit logs

**Typical Tasks**:
- Create radiologist accounts
- Monitor system health
- Update AI models
- Review security logs
- Configure alerts

**How to Create Admin** (requires existing admin):
```python
# Via Python console
from api.user_management import get_user_manager, UserCreate

user_mgr = get_user_manager()
admin = user_mgr.create_user(UserCreate(
    username="dr.admin",
    email="admin@hospital.com",
    password="SecurePass123!",
    role="admin",
    full_name="Dr. Admin Name"
))
```

---

### Radiologist

**Can Do**:
- ✅ Review AI predictions
- ✅ Confirm correct diagnoses
- ✅ Correct wrong diagnoses
- ✅ Request new inferences
- ✅ View their review history
- ✅ See agreement metrics

**Cannot Do**:
- ❌ Access other hospitals' data
- ❌ Manage users
- ❌ Configure system
- ❌ Delete data

**Daily Workflow**:
1. Login to dashboard
2. See pending reviews (AI needs confirmation)
3. For each case:
   - View medical image
   - View AI prediction + confidence
   - **Confirm** if correct (1 click)
   - **Correct** if wrong (select right diagnosis)
   - **Skip** if unsure
4. System automatically improves

**Time**: 30-60 seconds per case

---

### Hospital Admin

**Can Do**:
- ✅ Create radiologists in their hospital
- ✅ View hospital performance metrics
- ✅ Deactivate users in their hospital
- ✅ Export hospital reports

**Use Case**: Department head managing radiologist team

---

### Viewer

**Can Do**:
- ✅ View reviews (read-only)
- ✅ See metrics and reports
- ✅ Monitor system status

**Use Case**: Researchers, quality assurance, hospital leadership

---

## Radiologist Workflow

### Accessing the System

**URL**: http://[server-address]:8000/radiologist

**Login**:
```
Username: your_username
Password: your_password
```

**First Time Login**:
- You'll be prompted to change password
- Minimum 8 characters
- Must include: uppercase, lowercase, digit

---

### Dashboard Overview

**Main Sections**:

1. **Pending Reviews** (🔴 Red Badge)
   - AI predictions waiting for your confirmation
   - Sorted by: Most recent first
   - Shows: Image preview, AI prediction, confidence

2. **Recent Reviews** (✅ Green)
   - Your recently confirmed cases
   - Shows agreement rate with AI

3. **Statistics**
   - Total reviews: Your lifetime reviews
   - Agreement rate: How often you agree with AI
   - Today's reviews: Cases reviewed today

---

### Reviewing a Case

**Step-by-Step**:

1. **Click "Review" on pending case**
   
2. **See Case Details**:
   ```
   Medical Image: [Full-size view with zoom/pan]
   
   AI Prediction: Pneumonia
   Confidence: 87.3%
   
   Model: pneumonia_detector v2.1
   Date: 2025-11-23 14:35:12
   ```

3. **Make Decision**:

   **Option A - AI is Correct**:
   ```
   ✅ Confirm: Pneumonia
   ```
   - Click "Confirm"
   - Case marked reviewed
   - AI learns it was right

   **Option B - AI is Wrong**:
   ```
   ❌ AI said: Pneumonia
   ✅ Correct diagnosis: Normal
   ```
   - Select correct diagnosis from dropdown
   - Click "Submit Correction"
   - AI learns from mistake (supervised learning)

   **Option C - Unsure**:
   ```
   ⏭️ Skip
   ```
   - Case stays in pending queue
   - You can review later
   - No training happens

4. **Add Notes** (Optional):
   ```
   Comments: Right lower lobe infiltrate visible.
            Classic presentation.
   ```

5. **Submit**:
   - Confirmation saved to database
   - Training automatically triggered
   - Next case loads

**Time**: 30-60 seconds per case

---

### Understanding AI Predictions

**Confidence Scores**:
- **90-100%**: Very confident (likely correct)
- **70-89%**: Moderately confident (review carefully)
- **Below 70%**: Low confidence (high chance of error)

**What to Check**:
1. Image quality (blur, artifacts)
2. Anatomical landmarks visible
3. Pathology consistent with diagnosis
4. Consider patient history (if available)

**When AI is Wrong**:
- Low-quality images
- Rare conditions
- Subtle findings
- Atypical presentations

**Your Role**: Expert oversight, not replacement

---

### Batch Review Mode

**For High Volume**:
```
1. Click "Batch Review"
2. Review multiple cases in sequence
3. Keyboard shortcuts:
   - Spacebar: Confirm
   - 1-9: Select diagnosis
   - S: Skip
   - Enter: Next case
```

**Efficiency**: 100+ cases/hour possible

---

## System Administration

### User Management

#### Creating Users

**Via Web Interface** (Coming Soon):
- Login as admin
- Navigate to: Users → Create New
- Fill form, assign role
- User receives email with temporary password

**Via Python** (Current):
```python
from api.user_management import get_user_manager, UserCreate

user_mgr = get_user_manager()

# Create radiologist
radiologist = user_mgr.create_user(UserCreate(
    username="dr.smith",
    email="smith@hospital.com",
    password="TempPass123!",
    role="radiologist",
    hospital_id="hospital_001",
    full_name="Dr. Jane Smith"
))

print(f"✓ User created: {radiologist['username']}")
```

---

#### Deactivating Users

```python
user_mgr.delete_user(user_id)  # Soft delete (deactivate)
```

**Effect**:
- User cannot login
- Data preserved
- Can be reactivated

---

#### Resetting Passwords

```python
# Admin resets user password
new_password = "NewSecurePass123!"
user_mgr.change_password(user_id, old_password, new_password)
```

---

### Backup Management

**Automatic Backups**:
- **Frequency**: Every 24 hours (configurable)
- **Retention**: 30 days (configurable)
- **Location**: `./backups/`
- **Format**: Compressed tar.gz

**What's Backed Up**:
- Database (all reviews, labels, audit logs)
- Model weights (.pth, .pt files)
- Configuration files (.env, config.py)
- Recent logs (last 7 days)

**Manual Backup**:
```python
from api.backup_manager import get_backup_manager

backup_mgr = get_backup_manager()

# Create full backup
backup_path = backup_mgr.create_backup(backup_type="full")
print(f"Backup created: {backup_path}")

# Create database-only backup
backup_mgr.create_backup(backup_type="database")
```

**Restore from Backup**:
```python
# List available backups
backups = backup_mgr.list_backups()
for backup in backups:
    print(f"{backup['filename']} - {backup['size_formatted']}")

# Restore
success = backup_mgr.restore_backup(
    "backups/backup_full_20251123_143025.tar.gz",
    restore_type="full"
)
```

**⚠️ Before Restore**:
1. Stop server
2. Backup current data
3. Restore
4. Restart server

---

### Monitoring & Alerts

**What's Monitored**:
- ✅ Disk space (alert < 10 GB)
- ✅ Model accuracy (alert if drops >10%)
- ✅ Error rate (alert if >5%)
- ✅ System uptime
- ✅ Database size

**Alert Channels**:
- Email (SMTP)
- Slack (webhook)
- Log files

**Configure Alerts**:
```bash
# Edit .env file
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@hospital.com
SMTP_PASS=app_password
ALERT_EMAIL=admin@hospital.com
SLACK_WEBHOOK=https://hooks.slack.com/services/...
```

**Alert Example**:
```
🔴 ERROR: model

Model accuracy dropped to 65%

Level: ERROR
Category: model
Time: 2025-11-23 14:35:12

Details:
  previous: 85%
  current: 65%
  samples: 150
```

**Response Actions**:
1. Check recent model updates
2. Review recent cases (data quality)
3. Investigate system logs
4. Contact support if persists

---

### Database Migration (SQLite → PostgreSQL)

**When to Migrate**:
- More than 10,000 cases
- Multiple hospitals
- High concurrent users (10+)
- Need for advanced queries

**Migration Steps**:

1. **Install PostgreSQL**:
```bash
# Ubuntu
sudo apt install postgresql postgresql-contrib

# Windows
# Download from postgresql.org
```

2. **Create Database**:
```sql
CREATE DATABASE medical_ai;
CREATE USER medical_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE medical_ai TO medical_user;
```

3. **Update Configuration**:
```bash
# Edit .env
DATABASE_URL=postgresql://medical_user:secure_password@localhost/medical_ai
```

4. **Run Migration**:
```python
from database.migrations import DatabaseMigrator

migrator = DatabaseMigrator()
success = migrator.migrate_sqlite_to_postgres(
    "postgresql://medical_user:secure_password@localhost/medical_ai"
)

if success:
    print("✓ Migration complete")
```

5. **Verify**:
```python
# Check data integrity
import psycopg2
conn = psycopg2.connect("postgresql://...")
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM labeled_data")
print(f"Migrated {cursor.fetchone()[0]} reviews")
```

6. **Restart Server**:
```bash
# Server will auto-detect PostgreSQL
start_server.bat
```

---

## Troubleshooting

### Common Issues

#### Issue: Server Won't Start

**Symptoms**:
```
Error: Address already in use
```

**Solution**:
```bash
# Check what's using port 8000
netstat -ano | findstr :8000  # Windows
lsof -i :8000  # Linux/Mac

# Kill process or change port in .env
PORT=8001
```

---

#### Issue: Can't Login

**Symptoms**:
```
401 Unauthorized
Invalid credentials
```

**Solutions**:

1. **Check username/password** (case-sensitive)

2. **Account locked** (5 failed attempts):
```python
from api.user_management import get_user_manager
user_mgr = get_user_manager()

# Unlock user
conn = user_mgr.get_connection()
cursor = conn.cursor()
cursor.execute("""
    UPDATE users 
    SET locked_until = NULL, failed_login_attempts = 0
    WHERE username = ?
""", ("dr.smith",))
conn.commit()
```

3. **Reset password** (admin):
```python
user = user_mgr.get_user_by_username("dr.smith")
user_mgr.change_password(user['user_id'], old_pass, new_pass)
```

---

#### Issue: AI Predictions Failing

**Symptoms**:
```
Model temporarily unavailable
Inference timeout
```

**Solutions**:

1. **Check model files exist**:
```bash
ls models/weights/
# Should see .pth or .pt files
```

2. **Check GPU/memory**:
```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
```

3. **Restart server**:
```bash
# Stop server
# Wait 10 seconds
# Start server
```

4. **Check logs**:
```bash
tail -f logs/server.log
# Look for errors
```

---

#### Issue: Slow Performance

**Symptoms**:
- Inference takes >10 seconds
- Dashboard sluggish
- Timeouts

**Solutions**:

1. **Check CPU/GPU usage**:
```bash
# Windows
Task Manager → Performance

# Linux
htop
nvidia-smi  # If GPU
```

2. **Increase workers**:
```bash
# Edit .env
WORKERS=8
PROCESS_POOL_WORKERS=16
```

3. **Enable GPU** (if available):
```bash
# Edit .env
DEVICE=cuda
```

4. **Optimize database**:
```bash
# SQLite
sqlite3 labeled_data.db "VACUUM;"

# PostgreSQL
psql medical_ai -c "VACUUM ANALYZE;"
```

5. **Clear old logs**:
```bash
# Keep only last 30 days
find logs/ -name "*.log" -mtime +30 -delete
```

---

### System Logs

**Log Locations**:
```
logs/
├── server.log          # Main application log
├── access.log          # HTTP requests
├── error.log           # Errors only
└── audit.log           # Security events
```

**View Recent Errors**:
```bash
tail -100 logs/error.log
```

**Search Logs**:
```bash
grep "ERROR" logs/server.log | tail -20
grep "user_id=12345" logs/audit.log
```

**Log Rotation** (automatic):
- Daily rotation
- 30-day retention
- Compressed archives

---

## Security & Compliance

### HIPAA Compliance

**Technical Safeguards** ✅:
- ✅ Encryption at rest (AES-256)
- ✅ Encryption in transit (TLS 1.2+)
- ✅ Access controls (JWT authentication)
- ✅ Audit logging (all actions tracked)
- ✅ Session management (token expiration)

**Administrative Safeguards** ⚠️:
- Require hospital policies:
  - Business Associate Agreement (BAA)
  - Security risk assessment
  - Breach notification plan
  - User training

**Physical Safeguards** (Hospital Responsibility):
- Server room access control
- Hardware security
- Disaster recovery

---

### Audit Trail

**What's Logged**:
- Every login/logout
- Every review submission
- Every model inference
- Every user creation/deletion
- Every configuration change

**View Audit Log**:
```python
from monitoring.audit_logger import get_audit_logger

audit = get_audit_logger()
events = audit.get_recent_events(limit=100)

for event in events:
    print(f"{event['timestamp']} | {event['user_id']} | {event['action']}")
```

**Export for Compliance**:
```python
import pandas as pd

events = audit.get_events_by_date('2025-01-01', '2025-12-31')
df = pd.DataFrame(events)
df.to_csv('audit_2025.csv', index=False)
```

---

### Security Best Practices

**Passwords**:
- ✅ Minimum 8 characters
- ✅ Uppercase + lowercase + digit
- ❌ Never share passwords
- ✅ Change every 90 days
- ✅ Use password manager

**Network Security**:
- ✅ Use VPN for remote access
- ✅ Firewall rules (only port 8000)
- ✅ Valid SSL certificate (not self-signed)
- ❌ Don't expose to public internet

**Data Security**:
- ✅ Regular backups (automated)
- ✅ Test restores quarterly
- ✅ Encrypt backups
- ✅ Store backups off-site

**User Management**:
- ✅ Principle of least privilege
- ✅ Deactivate terminated users immediately
- ✅ Review user list monthly
- ✅ Audit admin actions

---

## API Reference

**Full API Documentation**: http://localhost:8000/docs

### Authentication

**Get Token**:
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "hospital_id": "hospital_001",
    "password": "your_password"
  }'
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Use Token**:
```bash
curl -X GET "http://localhost:8000/models/list" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Common Endpoints

**Upload Image for Inference**:
```bash
curl -X POST "http://localhost:8000/inference/chest_xray" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@path/to/xray.jpg" \
  -F "hospital_id=hospital_001"
```

**Get Pending Reviews**:
```bash
curl -X GET "http://localhost:8000/radiologist/pending-reviews" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Submit Review**:
```bash
curl -X POST "http://localhost:8000/radiologist/submit-review" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "review_id": "review_abc123",
    "radiologist_label": "Pneumonia",
    "action": "confirm",
    "comments": "Clear infiltrate visible"
  }'
```

---

## Support

**Technical Issues**:
- Email: support@medical-ai.com
- GitHub: github.com/yourusername/medical-ai-server
- Documentation: /docs/

**Emergency Contact**:
- 24/7 Hotline: +1-800-XXX-XXXX
- Response Time: 4 hours

**Training**:
- Online course: medical-ai.com/training
- Duration: 2 hours
- Certificate provided

---

**Document Version**: 2.0  
**Last Updated**: November 23, 2025  
**Next Review**: Quarterly
