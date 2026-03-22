#!/bin/bash
set -e

echo "========================================================"
echo "   Medora AI - VM Setup Script                          "
echo "========================================================"

# 1. Install System Dependencies
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv nginx libgl1-mesa-glx build-essential

# 2. Setup Python Environment
echo "Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip

# Install requirements
echo "Installing Python packages..."
# Install CPU-only Torch first to save space (Critical for 8GB VMs)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Remove torch from requirements.txt to prevent reinstalling huge CUDA version
sed -i '/torch/d' requirements.txt
sed -i '/torchvision/d' requirements.txt

# Install others (ignoring torch since we installed it)
pip install -r requirements.txt

# 3. Model Setup
echo "Checking models..."
# Run the downloader (it skips if files exist)
python scripts/download_more_models.py

# 4. Setup Gunicorn Systemd Service
echo "Configuring Gunicorn Service..."
cat <<EOF | sudo tee /etc/systemd/system/medora.service
[Unit]
Description=Gunicorn instance to serve Medora AI
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/medora-ai
Environment="PATH=/home/ubuntu/medora-ai/venv/bin"
ExecStart=/home/ubuntu/medora-ai/venv/bin/gunicorn --workers 3 --worker-class uvicorn.workers.UvicornWorker --bind unix:medora.sock -m 007 main:app --timeout 120

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl start medora
sudo systemctl enable medora

# 5. Setup Nginx
echo "Configuring Nginx..."
cat <<EOF | sudo tee /etc/nginx/sites-available/medora
server {
    listen 80;
    server_name _;

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ubuntu/medora-ai/medora.sock;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/medora /etc/nginx/sites-enabled
sudo rm -f /etc/nginx/sites-enabled/default

# Restart Nginx
sudo nginx -t
sudo systemctl restart nginx

# 6. Database Init
echo "Initializing Database..."
python scripts/check_and_seed_data.py

echo ""
echo "========================================================"
echo "✅ SETUP COMPLETE!"
echo "Your app should be live at http://<VM_IP>"
echo "========================================================"
