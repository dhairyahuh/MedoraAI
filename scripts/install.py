#!/usr/bin/env python3
"""
One-Command Installer for Medical Inference Server
Makes deployment trivial - handles everything automatically
"""
import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
import secrets
import json

class Installer:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent
        self.venv_path = self.base_dir / ".venv"
        self.config_file = self.base_dir / ".env"
        self.is_windows = platform.system() == "Windows"
        
    def print_header(self, message):
        print("\n" + "="*70)
        print(f"  {message}")
        print("="*70 + "\n")
        
    def run_command(self, cmd, check=True, shell=False):
        """Run command and return output"""
        try:
            if isinstance(cmd, str) and not shell:
                cmd = cmd.split()
            result = subprocess.run(cmd, check=check, capture_output=True, text=True, shell=shell)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return False, e.stdout, e.stderr
        except Exception as e:
            return False, "", str(e)
    
    def check_python_version(self):
        """Ensure Python 3.8+"""
        self.print_header("Step 1: Checking Python Version")
        version = sys.version_info
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} detected")
        
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print("❌ ERROR: Python 3.8 or higher required")
            print("   Please upgrade Python and try again")
            sys.exit(1)
        
        print("✓ Python version compatible")
        
    def create_virtual_environment(self):
        """Create Python virtual environment"""
        self.print_header("Step 2: Creating Virtual Environment")
        
        if self.venv_path.exists():
            print("⚠️  Virtual environment already exists")
            response = input("   Delete and recreate? (y/N): ").strip().lower()
            if response == 'y':
                print("   Deleting existing environment...")
                shutil.rmtree(self.venv_path)
            else:
                print("   Using existing environment")
                return
        
        print("Creating virtual environment...")
        success, stdout, stderr = self.run_command(f"{sys.executable} -m venv {self.venv_path}")
        
        if not success:
            print(f"❌ Failed to create virtual environment: {stderr}")
            sys.exit(1)
            
        print("✓ Virtual environment created")
        
    def get_pip_path(self):
        """Get path to pip in virtual environment"""
        if self.is_windows:
            return self.venv_path / "Scripts" / "pip.exe"
        else:
            return self.venv_path / "bin" / "pip"
    
    def get_python_path(self):
        """Get path to python in virtual environment"""
        if self.is_windows:
            return self.venv_path / "Scripts" / "python.exe"
        else:
            return self.venv_path / "bin" / "python"
        
    def install_dependencies(self):
        """Install Python packages"""
        self.print_header("Step 3: Installing Dependencies")
        
        pip_path = self.get_pip_path()
        
        print("Upgrading pip...")
        self.run_command(f"{pip_path} install --upgrade pip")
        
        print("\nInstalling core dependencies...")
        requirements_file = self.base_dir / "requirements.txt"
        
        if not requirements_file.exists():
            print("❌ requirements.txt not found")
            sys.exit(1)
        
        success, stdout, stderr = self.run_command(f"{pip_path} install -r {requirements_file}")
        
        if not success:
            print(f"⚠️  Some packages failed to install: {stderr}")
            print("   Continuing anyway...")
        else:
            print("✓ Dependencies installed")
        
        # Install PyTorch with CUDA if available
        print("\nChecking GPU availability...")
        python_path = self.get_python_path()
        success, stdout, stderr = self.run_command(
            f'{python_path} -c "import torch; print(torch.cuda.is_available())"'
        )
        
        if success and "True" in stdout:
            print("✓ GPU detected - PyTorch should use CUDA")
        else:
            print("ℹ️  No GPU detected - will use CPU (slower inference)")
            
    def setup_database(self):
        """Initialize database schema"""
        self.print_header("Step 4: Setting Up Database")
        
        python_path = self.get_python_path()
        
        # Run database initialization script
        init_script = self.base_dir / "scripts" / "init_database.py"
        
        if init_script.exists():
            print("Running database initialization...")
            success, stdout, stderr = self.run_command(f"{python_path} {init_script}")
            if success:
                print("✓ Database initialized")
            else:
                print(f"⚠️  Database initialization had issues: {stderr}")
        else:
            print("ℹ️  No database init script found - will be created on first run")
            
    def generate_secrets(self):
        """Generate secure secrets for JWT and API keys"""
        self.print_header("Step 5: Generating Security Keys")
        
        jwt_secret = secrets.token_urlsafe(64)
        api_key = secrets.token_urlsafe(32)
        admin_password = secrets.token_urlsafe(16)
        
        print("✓ JWT secret generated")
        print("✓ API key generated")
        print("✓ Admin password generated")
        
        return jwt_secret, api_key, admin_password
        
    def create_ssl_certificates(self):
        """Create self-signed SSL certificates for development"""
        self.print_header("Step 6: SSL Certificates")
        
        certs_dir = self.base_dir / "certs"
        certs_dir.mkdir(exist_ok=True)
        
        cert_file = certs_dir / "cert.pem"
        key_file = certs_dir / "key.pem"
        
        if cert_file.exists() and key_file.exists():
            print("✓ SSL certificates already exist")
            return
        
        # Check if openssl is available
        success, _, _ = self.run_command("openssl version", check=False)
        
        if not success:
            print("⚠️  OpenSSL not found - skipping SSL certificate generation")
            print("   For production, install valid SSL certificates manually")
            return
        
        print("Generating self-signed SSL certificates...")
        cmd = f'openssl req -x509 -newkey rsa:4096 -nodes -out {cert_file} -keyout {key_file} -days 365 -subj "/CN=localhost"'
        
        success, stdout, stderr = self.run_command(cmd, shell=True)
        
        if success:
            print("✓ Self-signed SSL certificates created")
            print("   ⚠️  WARNING: These are for DEVELOPMENT ONLY")
            print("   ⚠️  For production, replace with valid SSL certificates")
        else:
            print(f"⚠️  Failed to generate certificates: {stderr}")
            
    def create_env_file(self, jwt_secret, api_key, admin_password):
        """Create .env configuration file"""
        self.print_header("Step 7: Creating Configuration File")
        
        if self.config_file.exists():
            print("⚠️  .env file already exists")
            response = input("   Overwrite? (y/N): ").strip().lower()
            if response != 'y':
                print("   Keeping existing configuration")
                return
        
        # Get configuration from user
        print("\nConfiguration Options:")
        print("(Press Enter to use default values)")
        
        host = input("\nServer host [0.0.0.0]: ").strip() or "0.0.0.0"
        port = input("Server port [8000]: ").strip() or "8000"
        workers = input("Number of workers [4]: ").strip() or "4"
        
        # Database choice
        print("\nDatabase type:")
        print("  1. SQLite (default, easy setup)")
        print("  2. PostgreSQL (production-ready)")
        db_choice = input("Choose [1]: ").strip() or "1"
        
        if db_choice == "2":
            db_url = input("PostgreSQL URL [postgresql://user:pass@localhost/medical_ai]: ").strip()
            db_url = db_url or "postgresql://user:pass@localhost/medical_ai"
        else:
            db_url = "sqlite:///./labeled_data.db"
        
        # Email alerting
        print("\nEmail Alerting (optional):")
        smtp_server = input("SMTP server (leave blank to skip): ").strip()
        if smtp_server:
            smtp_port = input("SMTP port [587]: ").strip() or "587"
            smtp_user = input("SMTP username: ").strip()
            smtp_pass = input("SMTP password: ").strip()
            alert_email = input("Alert recipient email: ").strip()
        else:
            smtp_server = ""
            smtp_port = ""
            smtp_user = ""
            smtp_pass = ""
            alert_email = ""
        
        # Write .env file
        env_content = f"""# Medical Inference Server Configuration
# Generated by installer on {os.popen('date').read().strip() if not self.is_windows else 'install'}

# Server Configuration
HOST={host}
PORT={port}
WORKERS={workers}
RELOAD=False

# Security
JWT_SECRET={jwt_secret}
API_KEYS={api_key}
ADMIN_PASSWORD={admin_password}

# Database
DATABASE_URL={db_url}

# Model Configuration
DEVICE=cuda  # Will auto-detect GPU, fallback to CPU
MODEL_TIMEOUT=120
CONFIDENCE_THRESHOLD=0.8

# Queue Configuration
MAX_QUEUE_SIZE=10000
NUM_ASYNC_WORKERS=4
PROCESS_POOL_WORKERS=8

# Federated Learning
ENABLE_FEDERATED_LEARNING=True
DIFFERENTIAL_PRIVACY_EPSILON=0.1
BATCH_TRAINING_INTERVAL=7200  # 2 hours

# Email Alerting (optional)
SMTP_SERVER={smtp_server}
SMTP_PORT={smtp_port}
SMTP_USER={smtp_user}
SMTP_PASS={smtp_pass}
ALERT_EMAIL={alert_email}

# Backup Configuration
ENABLE_BACKUPS=True
BACKUP_INTERVAL=86400  # 24 hours
BACKUP_RETENTION_DAYS=30
BACKUP_PATH=./backups

# SSL/TLS
SSL_CERT_FILE=./certs/cert.pem
SSL_KEY_FILE=./certs/key.pem

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/server.log
"""
        
        with open(self.config_file, 'w') as f:
            f.write(env_content)
        
        print(f"\n✓ Configuration file created: {self.config_file}")
        print("\n📝 IMPORTANT CREDENTIALS:")
        print(f"   API Key: {api_key}")
        print(f"   Admin Password: {admin_password}")
        print("\n⚠️  Save these credentials securely!")
        
    def create_directories(self):
        """Create required directories"""
        self.print_header("Step 8: Creating Directory Structure")
        
        directories = [
            "logs",
            "backups",
            "certs",
            "models/weights",
            "federated_data",
            "static/test_images",
            "dataset images"
        ]
        
        for dir_path in directories:
            full_path = self.base_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created: {dir_path}")
            
    def create_startup_scripts(self):
        """Create convenient startup scripts"""
        self.print_header("Step 9: Creating Startup Scripts")
        
        python_path = self.get_python_path()
        main_script = self.base_dir / "main.py"
        
        if self.is_windows:
            # Windows batch file
            batch_content = f"""@echo off
echo Starting Medical Inference Server...
"{python_path}" "{main_script}"
pause
"""
            batch_file = self.base_dir / "start_server.bat"
            with open(batch_file, 'w') as f:
                f.write(batch_content)
            print(f"✓ Created: start_server.bat")
            
            # PowerShell script
            ps_content = f"""# Start Medical Inference Server
Write-Host "Starting Medical Inference Server..." -ForegroundColor Green
& "{python_path}" "{main_script}"
"""
            ps_file = self.base_dir / "start_server.ps1"
            with open(ps_file, 'w') as f:
                f.write(ps_content)
            print(f"✓ Created: start_server.ps1")
            
        else:
            # Linux/Mac bash script
            bash_content = f"""#!/bin/bash
echo "Starting Medical Inference Server..."
"{python_path}" "{main_script}"
"""
            bash_file = self.base_dir / "start_server.sh"
            with open(bash_file, 'w') as f:
                f.write(bash_content)
            # Make executable
            os.chmod(bash_file, 0o755)
            print(f"✓ Created: start_server.sh")
            
    def run_health_check(self):
        """Verify installation"""
        self.print_header("Step 10: Running Health Check")
        
        python_path = self.get_python_path()
        
        # Check if all required packages are installed
        print("Checking core dependencies...")
        packages = [
            "fastapi",
            "uvicorn",
            "torch",
            "torchvision",
            "Pillow",
            "numpy"
        ]
        
        all_ok = True
        for package in packages:
            success, stdout, stderr = self.run_command(
                f'{python_path} -c "import {package}"',
                check=False
            )
            if success:
                print(f"  ✓ {package}")
            else:
                print(f"  ❌ {package} - NOT FOUND")
                all_ok = False
        
        if all_ok:
            print("\n✓ All dependencies installed correctly")
        else:
            print("\n⚠️  Some dependencies are missing")
            print("   Run: pip install -r requirements.txt")
        
        return all_ok
        
    def print_next_steps(self):
        """Print what to do next"""
        self.print_header("Installation Complete!")
        
        print("✅ Medical Inference Server is ready to use!\n")
        
        print("📋 NEXT STEPS:\n")
        print("1. Start the server:")
        if self.is_windows:
            print("   • Double-click: start_server.bat")
            print("   • Or run: .venv\\Scripts\\python.exe main.py")
        else:
            print("   • Run: ./start_server.sh")
            print("   • Or: .venv/bin/python main.py")
        
        print("\n2. Access the system:")
        print("   • Radiologist Dashboard: http://localhost:8000/radiologist")
        print("   • Monitoring Dashboard: http://localhost:8000/monitoring/dashboard")
        print("   • API Documentation: http://localhost:8000/docs")
        
        print("\n3. Upload medical images:")
        print("   • Use the web interface or API")
        print("   • Supported: JPG, PNG, DICOM")
        
        print("\n4. Review AI predictions:")
        print("   • Login to radiologist dashboard")
        print("   • Confirm or correct diagnoses")
        print("   • System learns from your corrections")
        
        print("\n📚 DOCUMENTATION:")
        print("   • Quick Start: QUICK_START.md")
        print("   • Deployment Guide: DEPLOYMENT_GUIDE.md")
        print("   • Hospital Readiness: HOSPITAL_DEPLOYMENT_READINESS.md")
        
        print("\n🔐 SECURITY NOTES:")
        print("   • SSL certificates are self-signed (dev only)")
        print("   • For production: Install valid SSL certificates")
        print("   • Credentials stored in: .env")
        
        print("\n💾 BACKUP:")
        print("   • Automatic backups enabled (every 24 hours)")
        print("   • Location: ./backups/")
        
        print("\n⚠️  BEFORE CLINICAL USE:")
        print("   • Read: HOSPITAL_DEPLOYMENT_READINESS.md")
        print("   • Get IRB approval")
        print("   • Obtain liability insurance")
        print("   • Label system: 'Research Use Only'")
        
        print("\n" + "="*70)
        print("  Need help? Check the documentation or run: python health_check.py")
        print("="*70 + "\n")
        
    def run(self):
        """Execute full installation"""
        print("\n")
        print("╔═══════════════════════════════════════════════════════════════════╗")
        print("║                                                                   ║")
        print("║     Medical AI Inference Server - Automated Installer            ║")
        print("║     One-Command Setup for Hospital Deployment                    ║")
        print("║                                                                   ║")
        print("╚═══════════════════════════════════════════════════════════════════╝")
        
        try:
            self.check_python_version()
            self.create_virtual_environment()
            self.install_dependencies()
            self.setup_database()
            
            jwt_secret, api_key, admin_password = self.generate_secrets()
            
            self.create_ssl_certificates()
            self.create_env_file(jwt_secret, api_key, admin_password)
            self.create_directories()
            self.create_startup_scripts()
            
            health_ok = self.run_health_check()
            
            self.print_next_steps()
            
            return 0 if health_ok else 1
            
        except KeyboardInterrupt:
            print("\n\n❌ Installation cancelled by user")
            return 1
        except Exception as e:
            print(f"\n\n❌ Installation failed: {e}")
            import traceback
            traceback.print_exc()
            return 1

if __name__ == "__main__":
    installer = Installer()
    sys.exit(installer.run())
