#!/bin/bash
set -e
APP_DIR="/var/www/medora"

echo "Re-deploying to $APP_DIR..."

# Ensure Directory
sudo mkdir -p $APP_DIR
# Give current user permissions
sudo chown -R $USER:$USER $APP_DIR

# Copy Files (from rsync destination)
echo "Copying files..."
cp -r ~/MedoraAI/* $APP_DIR/

cd $APP_DIR

# Venv
if [ ! -d "venv" ]; then
    echo "Creating venv..."
    python3 -m venv venv
fi

echo "Installing Dependencies..."
source venv/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    pip install gunicorn uvloop
else
    echo "requirements.txt missing in target!"
    exit 1
fi

# Permissions fix (allow www-data to read, but User to write)
echo "Fixing Permissions..."
sudo chown -R www-data:www-data $APP_DIR
sudo chmod -R 775 $APP_DIR
# Add current user to www-data group so we can modify
sudo usermod -a -G www-data $USER

# Finalize
echo "Running Final Config..."
# Need to use sudo for service/nginx ops
# And ensure path to script is correct
chmod +x deploy/finalize_setup.sh
./deploy/finalize_setup.sh
