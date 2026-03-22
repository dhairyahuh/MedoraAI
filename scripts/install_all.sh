#!/bin/bash
# Install all MedoraAI dependencies
# Run: bash install_all.sh

echo "=========================================="
echo "Installing ALL MedoraAI Dependencies"
echo "=========================================="
echo ""

# Check if venv is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated!"
    echo "Activating .venv..."
    source .venv/bin/activate
fi

echo "✓ Virtual environment: $VIRTUAL_ENV"
echo ""
echo "Installing packages from requirements.txt..."
echo "This may take 5-10 minutes..."
echo ""

# Install all dependencies
pip install --no-cache-dir -r requirements.txt

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Verifying key packages..."

# Verify installations
python -c "import fastapi; print('✓ FastAPI')" 2>/dev/null || echo "✗ FastAPI missing"
python -c "import cryptography; print('✓ cryptography')" 2>/dev/null || echo "✗ cryptography missing"
python -c "import jwt; print('✓ PyJWT')" 2>/dev/null || echo "✗ PyJWT missing"
python -c "import prometheus_client; print('✓ prometheus_client')" 2>/dev/null || echo "✗ prometheus_client missing"
python -c "import torch; print('✓ PyTorch')" 2>/dev/null || echo "✗ PyTorch missing"
python -c "import transformers; print('✓ Transformers')" 2>/dev/null || echo "✗ Transformers missing"

echo ""
echo "=========================================="
echo "You can now run: python main.py --no-ssl"
echo "=========================================="
