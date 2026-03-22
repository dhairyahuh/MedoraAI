# 🚀 Deployment Guide - Medical AI Inference Server

**Version**: 2.0  
**For**: Hospital IT Administrators  
**Deployment Time**: 30-60 minutes

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Hardware Requirements](#hardware-requirements)
3. [Installation Steps](#installation-steps)
4. [Configuration](#configuration)
5. [Security Hardening](#security-hardening)
6. [Testing Deployment](#testing-deployment)
7. [Go-Live Checklist](#go-live-checklist)
8. [Maintenance & Monitoring](#maintenance--monitoring)
9. [Scaling Guide](#scaling-guide)

---

## Pre-Deployment Checklist

### ✅ Hospital Requirements

**Administrative**:
- [ ] Business Associate Agreement (BAA) signed
- [ ] Security risk assessment completed
- [ ] HIPAA compliance review done
- [ ] IT department approval
- [ ] Radiology department buy-in

**Technical**:
- [ ] Server hardware procured
- [ ] Network configuration approved
- [ ] Firewall rules planned
- [ ] Backup storage available
- [ ] Email/alert system configured

**Personnel**:
- [ ] System administrator assigned
- [ ] Radiologists identified for pilot
- [ ] Training scheduled
- [ ] Support contact established

---

### ✅ Software Prerequisites

**Required**:
- Operating System: Ubuntu 22.04 LTS (recommended) or Windows Server 2019+
- Python: 3.8 - 3.12
- Database: SQLite (pilot) or PostgreSQL 13+ (production)
- Web browser: Chrome, Firefox, Safari, Edge (latest)

**Optional**:
- NVIDIA GPU with CUDA 11.8+ (for faster inference)
- Docker (for containerized deployment)
- Nginx/Apache (for reverse proxy)

---

## Hardware Requirements

### Pilot Deployment (10-50 cases/day, 1-5 users)

**Server**:
- CPU: 4 cores @ 2.5 GHz (Intel Xeon or AMD EPYC)
- RAM: 8 GB
- Storage: 100 GB SSD
- Network: 10 Mbps

**Estimated Cost**: $1,000 - $2,000 (hardware only)

**Example**: Dell PowerEdge R240, HP ProLiant ML110

---

### Production Deployment (100-500 cases/day, 10-50 users)

**Server**:
- CPU: 8-16 cores @ 3.0 GHz
- RAM: 32 GB (64 GB recommended)
- GPU: NVIDIA RTX 4090 or A4000 (16-24 GB VRAM)
- Storage: 500 GB NVMe SSD
- Network: 1 Gbps

**Database Server** (if separate):
- CPU: 4 cores
- RAM: 16 GB
- Storage: 250 GB SSD

**Estimated Cost**: $5,000 - $15,000 (hardware only)

**Example**: Dell PowerEdge R740, HP ProLiant DL380

---

### High-Volume Deployment (1000+ cases/day, 50+ users)

**Application Server** (load-balanced):
- 2-4 servers (specs above)
- Load balancer (Nginx, HAProxy, or AWS ELB)

**Database**: PostgreSQL cluster (primary + replica)

**Storage**: Network-attached storage (NAS) or S3-compatible

**Estimated Cost**: $50,000 - $150,000 (hardware + infrastructure)

---

## Installation Steps

### Method 1: Automated Install (Recommended)

**Step 1: Download Software**
```bash
# SSH into server
ssh admin@hospital-server.local

# Create directory
mkdir -p /opt/medical-ai
cd /opt/medical-ai

# Download release (replace URL with actual release)
wget https://github.com/yourusername/medical-ai-server/archive/v2.0.tar.gz
tar -xzf v2.0.tar.gz
cd medical-ai-server-2.0
```

---

**Step 2: Run Installer**
```bash
# Run automated installer
sudo python install.py
```

**Installer Prompts**:
```
========================================
Medical AI Inference Server Installer
========================================

Server host [0.0.0.0]: 0.0.0.0
Server port [8000]: 8000
Number of workers [4]: 8

Database type:
  1. SQLite (default, easy setup)
  2. PostgreSQL (production-ready)
Choose [1]: 2

PostgreSQL connection:
Host [localhost]: db.hospital.local
Port [5432]: 5432
Database [medical_ai]: medical_ai
Username: medical_user
Password: ********

Email Alerting:
SMTP server: smtp.hospital.com
SMTP port [587]: 587
SMTP username: alerts@hospital.com
SMTP password: ********
Alert recipient: admin@hospital.com

Slack Alerts (optional):
Slack webhook URL (leave blank to skip): https://hooks.slack.com/services/...

GPU Configuration:
CUDA available: Yes (NVIDIA RTX 4090)
Enable GPU? [Y/n]: Y

Generate SSL certificate? [Y/n]: Y
SSL certificate domain [localhost]: medical-ai.hospital.com

Creating virtual environment...
Installing dependencies...
Generating security keys...
Creating SSL certificates...
Initializing database...
Creating admin user...
Downloading models...

================================================================================
Installation Complete!
================================================================================

📝 SAVE THESE CREDENTIALS SECURELY:

Admin Username: admin
Admin Password: kL9mN2pQ5rS8tU1vW4xY7zA3bC6dE9fG
API Key: hI2jK5lM8nO1pQ4rS7tU0vW3xY6zA9bC1dE4fG7hI0jK3lM6nO9pQ2rS5tU8

⚠️  CHANGE ADMIN PASSWORD IMMEDIATELY AFTER FIRST LOGIN

🔒 Security Notes:
   - SSL certificate generated at: /opt/medical-ai/ssl/cert.pem
   - For production, replace with CA-signed certificate
   - Firewall: Only allow port 8000 from hospital network

📋 Next Steps:
1. Start server: sudo systemctl start medical-ai
2. Enable autostart: sudo systemctl enable medical-ai
3. Access dashboard: https://medical-ai.hospital.com:8000/radiologist
4. Change admin password
5. Create radiologist accounts
6. Run test inference
================================================================================
```

---

**Step 3: Start Server**
```bash
# Start server
sudo systemctl start medical-ai

# Enable autostart on boot
sudo systemctl enable medical-ai

# Check status
sudo systemctl status medical-ai
```

**Expected Output**:
```
● medical-ai.service - Medical AI Inference Server
   Loaded: loaded (/etc/systemd/system/medical-ai.service; enabled)
   Active: active (running) since Mon 2025-11-23 10:00:00 UTC; 5s ago
 Main PID: 12345 (python)
   Status: "Server started on http://0.0.0.0:8000"
```

---

### Method 2: Docker Deployment

**Step 1: Build Docker Image**
```bash
# Download Dockerfile
cd /opt/medical-ai
wget https://github.com/.../Dockerfile

# Build image
docker build -t medical-ai-server:2.0 .
```

**Step 2: Run Container**
```bash
docker run -d \
  --name medical-ai \
  --restart unless-stopped \
  -p 8000:8000 \
  -v /opt/medical-ai/data:/app/data \
  -v /opt/medical-ai/models:/app/models \
  -v /opt/medical-ai/backups:/app/backups \
  -e DATABASE_URL="postgresql://user:pass@db.hospital.local/medical_ai" \
  -e SMTP_SERVER="smtp.hospital.com" \
  -e SMTP_USER="alerts@hospital.com" \
  -e SMTP_PASS="password" \
  --gpus all \
  medical-ai-server:2.0
```

**Step 3: Verify**
```bash
docker logs medical-ai
docker exec -it medical-ai python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

---

## Configuration

### Environment Variables (.env)

**Required**:
```bash
# Server
HOST=0.0.0.0
PORT=8000
WORKERS=8

# Security
API_SECRET_KEY=<generated-by-installer>
JWT_SECRET_KEY=<generated-by-installer>
JWT_EXPIRATION_MINUTES=60

# Database
DATABASE_URL=postgresql://medical_user:password@localhost/medical_ai

# Device
DEVICE=cuda  # or 'cpu'
BATCH_SIZE=8

# Monitoring
SMTP_SERVER=smtp.hospital.com
SMTP_PORT=587
SMTP_USER=alerts@hospital.com
SMTP_PASS=password
ALERT_EMAIL=admin@hospital.com
```

**Optional**:
```bash
# Slack Alerts
SLACK_WEBHOOK=https://hooks.slack.com/services/...

# Backup
BACKUP_RETENTION_DAYS=30
BACKUP_DIRECTORY=./backups

# Performance
IMAGE_SIZE=224  # Preprocessing size
MAX_MEMORY_GB=16
PROCESS_POOL_WORKERS=16

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_RETENTION_DAYS=90
```

---

### Database Setup (PostgreSQL)

**Step 1: Install PostgreSQL**
```bash
# Ubuntu
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Step 2: Create Database**
```bash
sudo -u postgres psql

CREATE DATABASE medical_ai;
CREATE USER medical_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE medical_ai TO medical_user;

# Enable extensions
\c medical_ai
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

\q
```

**Step 3: Configure PostgreSQL**
```bash
# Edit postgresql.conf
sudo nano /etc/postgresql/14/main/postgresql.conf

# Increase connections
max_connections = 200

# Optimize for server RAM (example: 32GB server)
shared_buffers = 8GB
effective_cache_size = 24GB
maintenance_work_mem = 2GB
work_mem = 64MB

# Restart
sudo systemctl restart postgresql
```

**Step 4: Allow Remote Connections** (if DB on separate server)
```bash
# Edit pg_hba.conf
sudo nano /etc/postgresql/14/main/pg_hba.conf

# Add line (replace 192.168.1.0/24 with your network)
host    medical_ai    medical_user    192.168.1.0/24    scram-sha-256

# Edit postgresql.conf
listen_addresses = '*'  # Or specific IP

# Restart
sudo systemctl restart postgresql
```

---

### Firewall Configuration

**Ubuntu (UFW)**:
```bash
# Allow SSH (if remote)
sudo ufw allow 22/tcp

# Allow application
sudo ufw allow 8000/tcp

# Allow only from hospital network
sudo ufw allow from 192.168.1.0/24 to any port 8000

# Enable firewall
sudo ufw enable
```

**Windows Firewall**:
```powershell
# Allow port 8000
New-NetFirewallRule -DisplayName "Medical AI Server" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

# Restrict to hospital network
New-NetFirewallRule -DisplayName "Medical AI Server" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -RemoteAddress 192.168.1.0/24
```

---

## Security Hardening

### 1. SSL/TLS Certificate

**Option A: Self-Signed** (pilot only)
```bash
# Already generated by installer
ls ssl/cert.pem ssl/key.pem
```

**Option B: CA-Signed** (production)
```bash
# Generate CSR
openssl req -new -key ssl/key.pem -out ssl/cert.csr

# Submit CSR to hospital CA or public CA (Let's Encrypt, DigiCert)
# Receive signed certificate
# Replace ssl/cert.pem with signed certificate
```

**Configure Server**:
```bash
# Edit .env
SSL_CERT=/opt/medical-ai/ssl/cert.pem
SSL_KEY=/opt/medical-ai/ssl/key.pem
```

---

### 2. Reverse Proxy (Nginx)

**Install Nginx**:
```bash
sudo apt install nginx
```

**Configure**:
```nginx
# /etc/nginx/sites-available/medical-ai
server {
    listen 443 ssl http2;
    server_name medical-ai.hospital.com;

    ssl_certificate /opt/medical-ai/ssl/cert.pem;
    ssl_certificate_key /opt/medical-ai/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Max upload size (for medical images)
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for inference
        proxy_read_timeout 300s;
        proxy_connect_timeout 10s;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name medical-ai.hospital.com;
    return 301 https://$server_name$request_uri;
}
```

**Enable**:
```bash
sudo ln -s /etc/nginx/sites-available/medical-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

### 3. Operating System Hardening

**Update System**:
```bash
sudo apt update && sudo apt upgrade -y
```

**Disable Unused Services**:
```bash
sudo systemctl disable bluetooth
sudo systemctl disable cups
```

**Configure Automatic Updates**:
```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

**Set Up Intrusion Detection** (optional):
```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

---

### 4. User Access Control

**Create Service Account**:
```bash
# Run server as non-root user
sudo useradd -r -s /bin/false medical-ai

# Set permissions
sudo chown -R medical-ai:medical-ai /opt/medical-ai
sudo chmod -R 750 /opt/medical-ai
```

**Update Systemd Service**:
```ini
[Service]
User=medical-ai
Group=medical-ai
WorkingDirectory=/opt/medical-ai
```

---

### 5. Audit Logging

**Enable System Audit**:
```bash
sudo apt install auditd
sudo systemctl enable auditd

# Monitor application directory
sudo auditctl -w /opt/medical-ai -p wa -k medical_ai_changes
```

---

## Testing Deployment

### 1. Health Check

```bash
curl -k https://medical-ai.hospital.com:8000/health
```

**Expected**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-23T14:35:12Z",
  "components": {
    "database": "healthy",
    "models": "healthy",
    "gpu": "available"
  }
}
```

---

### 2. Authentication Test

```bash
# Login
curl -k -X POST https://medical-ai.hospital.com:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"hospital_id": "admin", "password": "your_password"}'
```

**Expected**:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

---

### 3. Inference Test

```bash
# Run test inference
python test_inference_endpoint.py
```

**Expected**:
```
Testing pneumonia_detector...
✓ Inference successful
  Prediction: Pneumonia
  Confidence: 87.3%
  Time: 0.124s
```

---

### 4. Database Test

```bash
# Check database connection
python -c "
from database.migrations import get_database_connection
conn = get_database_connection()
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM users')
print(f'Users: {cursor.fetchone()[0]}')
"
```

---

### 5. Backup Test

```bash
# Trigger manual backup
python -c "
from api.backup_manager import get_backup_manager
backup_mgr = get_backup_manager()
backup_path = backup_mgr.create_backup('full')
print(f'Backup created: {backup_path}')
"

# Verify backup
ls -lh backups/
```

---

### 6. Alert Test

```bash
# Trigger test alert
python -c "
from api.alert_manager import get_alert_manager
alert_mgr = get_alert_manager()
alert_mgr.send_alert(
    'INFO',
    'system',
    'Deployment test alert',
    {'test': True}
)
print('Alert sent - check email/Slack')
"
```

---

## Go-Live Checklist

### Pre-Launch (1 Week Before)

- [ ] All hardware installed and configured
- [ ] Software installed and tested
- [ ] Database initialized and optimized
- [ ] Backup system tested (create + restore)
- [ ] Alert system tested (email + Slack)
- [ ] SSL certificate installed (CA-signed for production)
- [ ] Firewall rules configured
- [ ] User accounts created for pilot radiologists
- [ ] Training completed for all users
- [ ] Documentation distributed
- [ ] Support contact established

---

### Launch Day

**Morning**:
- [ ] Verify server is running
- [ ] Check system resources (CPU, RAM, disk)
- [ ] Test inference endpoints
- [ ] Verify database connectivity
- [ ] Check alert system

**During Go-Live**:
- [ ] Monitor system in real-time
- [ ] Stand by for user questions
- [ ] Watch for errors in logs
- [ ] Track performance metrics

**End of Day**:
- [ ] Review system logs
- [ ] Check for any alerts
- [ ] Verify backups completed
- [ ] Document any issues
- [ ] Brief team on day 1 results

---

### Post-Launch (First Week)

- [ ] Daily monitoring of system health
- [ ] Review radiologist feedback
- [ ] Check model performance metrics
- [ ] Verify backup completion
- [ ] Address any issues promptly
- [ ] Weekly status report

---

## Maintenance & Monitoring

### Daily Tasks (Automated)

- ✅ Automated backups (default: 3 AM)
- ✅ Health checks (every 15 minutes)
- ✅ Log rotation
- ✅ Alert monitoring

---

### Weekly Tasks (Manual)

- [ ] Review system logs for errors
- [ ] Check disk space usage
- [ ] Verify backup integrity (test restore)
- [ ] Review alert history
- [ ] Check model performance metrics
- [ ] Update models if needed

---

### Monthly Tasks

- [ ] Security patch updates
- [ ] Database optimization (VACUUM, ANALYZE)
- [ ] User access review
- [ ] Performance analysis
- [ ] Backup retention cleanup
- [ ] Documentation updates

---

### Quarterly Tasks

- [ ] Full system audit
- [ ] Disaster recovery test
- [ ] Security assessment
- [ ] User training refresher
- [ ] Hardware inspection
- [ ] Capacity planning review

---

## Scaling Guide

### Vertical Scaling (Single Server)

**Increase Resources**:
1. Add more RAM (up to 64 GB)
2. Add GPU (NVIDIA RTX 4090 or A100)
3. Upgrade to NVMe SSD
4. Increase worker count

**Configuration**:
```bash
# Edit .env
WORKERS=16
PROCESS_POOL_WORKERS=32
MAX_MEMORY_GB=32
```

**Capacity**: Up to 500 cases/day, 50 concurrent users

---

### Horizontal Scaling (Multiple Servers)

**Architecture**:
```
                    Load Balancer (Nginx/HAProxy)
                            |
        +-------------------+-------------------+
        |                   |                   |
   App Server 1        App Server 2        App Server 3
        |                   |                   |
        +-------------------+-------------------+
                            |
                   PostgreSQL Primary
                            |
                   PostgreSQL Replica
```

**Setup**:

1. **Load Balancer**:
```nginx
upstream medical_ai_backend {
    least_conn;
    server 192.168.1.10:8000 weight=1;
    server 192.168.1.11:8000 weight=1;
    server 192.168.1.12:8000 weight=1;
}

server {
    listen 443 ssl;
    server_name medical-ai.hospital.com;
    
    location / {
        proxy_pass http://medical_ai_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

2. **Shared Storage** (for models):
```bash
# NFS mount on all app servers
sudo mount -t nfs 192.168.1.100:/medical-ai-models /opt/medical-ai/models
```

3. **Database Replication**:
```sql
-- On primary
CREATE PUBLICATION medical_ai_pub FOR ALL TABLES;

-- On replica
CREATE SUBSCRIPTION medical_ai_sub 
CONNECTION 'host=primary dbname=medical_ai user=replication_user password=pass'
PUBLICATION medical_ai_pub;
```

**Capacity**: 1000+ cases/day, 100+ concurrent users

---

**Document Version**: 2.0  
**Last Updated**: November 23, 2025  
**Next Review**: Quarterly
