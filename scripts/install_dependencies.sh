#!/bin/bash
# Quick install script for MedoraAI dependencies
# Run this: bash install_dependencies.sh

echo "Installing MedoraAI dependencies..."
echo "=================================="

# Activate venv if not already activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Install all dependencies
echo "Installing packages from requirements.txt..."
pip install --no-cache-dir -r requirements.txt

# Verify key packages
echo ""
echo "Verifying installation..."
python -c "import fastapi; print('✓ FastAPI installed')" 2>/dev/null || echo "✗ FastAPI missing"
python -c "import prometheus_client; print('✓ prometheus_client installed')" 2>/dev/null || echo "✗ prometheus_client missing"
python -c "import torch; print('✓ PyTorch installed')" 2>/dev/null || echo "✗ PyTorch missing"
python -c "import transformers; print('✓ Transformers installed')" 2>/dev/null || echo "✗ Transformers missing"

echo ""
echo "Installation complete!"
echo "Run: python main.py --no-ssl"
