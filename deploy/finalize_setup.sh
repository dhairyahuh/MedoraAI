#!/bin/bash
set -e
echo "Finalizing setup..."

# Nginx
echo "Configuring Nginx..."
sudo cp ~/MedoraAI/deploy/nginx_medora /etc/nginx/sites-available/medora
sudo ln -sf /etc/nginx/sites-available/medora /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# Environment Variables
echo "Configuring Environment..."
# Copy .env (assuming rsync brought it, or we create fresh)
if [ -f ~/MedoraAI/.env ]; then
    sudo cp ~/MedoraAI/.env /var/www/medora/.env
else
    # Create valid minimal .env
    sudo touch /var/www/medora/.env
    echo "SECRET_KEY=production_secret_key_change_me" | sudo tee -a /var/www/medora/.env
fi

# Ensure DATABASE_URL is correct for the Postgres we just installed
# Remove old DATABASE_URL if exists
sudo sed -i '/DATABASE_URL/d' /var/www/medora/.env
# Add correct URL
echo "DATABASE_URL=postgresql+psycopg2://medora_user:SecureMedoraPass2026!@localhost/medora_db" | sudo tee -a /var/www/medora/.env

# Permissions
sudo chown -R www-data:www-data /var/www/medora
sudo chmod -R 775 /var/www/medora

# Service
echo "Starting Service..."
sudo cp ~/MedoraAI/deploy/medora.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart medora
sudo systemctl enable medora

echo "Deployment Finalized! Application should be accessible on External IP."
