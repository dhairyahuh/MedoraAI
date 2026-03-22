# Installation Fix for zsh

## Issue
When installing packages with brackets in zsh, you need to quote them.

## Solution

### Option 1: Install from requirements.txt (Recommended)
```bash
# This works fine - pip handles brackets in requirements.txt
pip install --no-cache-dir -r requirements.txt
```

### Option 2: Install manually with quotes
If you need to install uvicorn manually in zsh:
```bash
# Quote the brackets for zsh
pip install "uvicorn[standard]==0.24.0"
```

### Option 3: Install base uvicorn + extras separately
```bash
pip install uvicorn==0.24.0
pip install websockets httptools  # Standard extras
```

## What's Fixed

1. ✅ **TensorFlow removed** - Not needed for Pneumonia model (uses PyTorch/Transformers)
2. ✅ **Requirements.txt updated** - Compatible with Python 3.13
3. ✅ **zsh bracket handling** - Use quotes when installing manually

## Quick Install Command

```bash
# Make sure venv is activated
source .venv/bin/activate

# Install all dependencies (TensorFlow skipped, uvicorn works)
pip install --no-cache-dir -r requirements.txt
```

This should now work without errors!
