# Quick Install Guide - Fix Missing Modules

## Problem
You're getting `ModuleNotFoundError` for various packages because dependencies aren't fully installed.

## Solution: Install ALL Dependencies at Once

Run this single command in your terminal:

```bash
# Make sure venv is activated
source .venv/bin/activate

# Install ALL dependencies (this will take a few minutes)
pip install --no-cache-dir -r requirements.txt
```

## What This Installs

- **Web Framework**: FastAPI, Uvicorn, python-multipart
- **Deep Learning**: PyTorch, Torchvision, Transformers
- **Monitoring**: prometheus-client, psutil
- **Security**: PyJWT (provides `jwt` module), cryptography, bcrypt
- **Image Processing**: Pillow, opencv-python
- **Scientific**: numpy, pandas, scikit-learn
- **And more...**

## After Installation

Verify key packages:
```bash
python -c "import fastapi; print('✓ FastAPI')"
python -c "import jwt; print('✓ PyJWT')"
python -c "import prometheus_client; print('✓ Prometheus')"
python -c "import torch; print('✓ PyTorch')"
python -c "import transformers; print('✓ Transformers')"
```

## Then Run Server

```bash
python main.py --no-ssl
```

## If Installation Fails

If you get errors, install packages in groups:

```bash
# Core web framework
pip install fastapi==0.104.1 "uvicorn[standard]==0.24.0" python-multipart==0.0.6

# Monitoring
pip install prometheus-client==0.19.0 psutil==5.9.6

# Security
pip install PyJWT==2.8.0 cryptography==41.0.7 bcrypt==4.1.2

# Deep Learning
pip install "torch>=2.8.0,<3.0.0" "torchvision>=0.19.0,<1.0.0" "transformers>=4.35.0,<5.0.0"

# Image processing
pip install "Pillow>=10.0.0,<11.0.0" "opencv-python>=4.8.0,<5.0.0"

# Scientific
pip install "numpy>=1.24.0,<2.0.0" "pandas>=2.0.0,<3.0.0" "scikit-learn>=1.3.0,<2.0.0"

# Rest of requirements
pip install --no-cache-dir -r requirements.txt
```
