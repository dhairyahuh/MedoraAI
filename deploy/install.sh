#!/bin/bash
# Installation Script for Medora AI on Ubuntu/Debian

set -e

echo "Starting deployment setup..."

# 1. Update System
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install Dependencies
sudo apt-get install -y python3-pip python3-venv postgresql postgresql-contrib nginx git certbot python3-certbot-nginx

# 3. Setup Database
echo "Configuring PostgreSQL..."
sudo -u postgres psql -c "CREATE DATABASE medora_db;" || echo "Database medora_db potentially already exists, skipping..."
sudo -u postgres psql -c "CREATE USER medora_user WITH PASSWORD 'SecureMedoraPass2026!';" || echo "User potentially exists..."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE medora_db TO medora_user;"

# 4. Setup Application Directory
APP_DIR="/var/www/medora"
sudo mkdir -p $APP_DIR
sudo chown -R $USER:$USER $APP_DIR

# 5. Setup Virtual Environment
python3 -m venv venv
source venv/bin/activate

# 6. Install Python Requirements
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    pip install gunicorn
else
    echo "requirements.txt not found!"
    exit 1
fi

echo "Installation complete. Next: Configure environment variables and run with systemd."
