#!/bin/bash
set -e

# Usage: ./scripts/upload_to_vm.sh <VM_IP> <SSH_KEY_PATH>

VM_IP=$1
SSH_KEY=$2

if [ -z "$VM_IP" ] || [ -z "$SSH_KEY" ]; then
    echo "Usage: $0 <VM_IP> <SSH_KEY_PATH>"
    exit 1
fi

echo "========================================================"
echo "   Medora AI - Uploading to VM ($VM_IP)                 "
echo "========================================================"

# Fix permissions for key
chmod 400 "$SSH_KEY"

# Ensure target directory exists
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no azureuser@$VM_IP "mkdir -p /home/azureuser/medora-ai"

# Sync files (excluding large models if preferred, but user wanted models)
# We exclude .venv, .git, and bulky temporary files
echo "Syncing files... (this may take time for 5GB models)"
rsync -avz --progress \
    --exclude '.venv' \
    --exclude '.git' \
    --exclude 'logs' \
    --exclude '__pycache__' \
    --exclude '*.DS_Store' \
    -e "ssh -i $SSH_KEY" \
    . azureuser@$VM_IP:/home/azureuser/medora-ai/

echo ""
echo "✅ Upload Complete!"
echo "Next step: Log in and run setup."
echo "ssh -i $SSH_KEY azureuser@$VM_IP"
