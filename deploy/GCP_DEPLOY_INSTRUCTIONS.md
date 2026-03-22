# Google Cloud Deployment Guide

## 1. Transfer Files
Copy the entire `MedoraAI` folder to your VM instance.
```bash
scp -r MedoraAI user@External_IP:~/
```

## 2. Connect to VM
```bash
ssh user@External_IP
cd MedoraAI/deploy
```

## 3. Run Setup
Make scripts executable and run install:
```bash
chmod +x install.sh
./install.sh
```

## 4. Environment Variables
Create the production `.env` file in `/var/www/medora/.env`:
```bash
sudo nano /var/www/medora/.env
```
Paste your content (update DATABASE_URL if external, or localhost if installed locally):
```
DATABASE_URL=postgresql+psycopg2://medora_user:SecureMedoraPass2026!@localhost/medora_db
SECRET_KEY=...
# etc
```

## 5. Configure Nginx
```bash
sudo cp nginx_medora /etc/nginx/sites-available/medora
sudo ln -s /etc/nginx/sites-available/medora /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

## 6. Start Service
```bash
sudo cp medora.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start medora
sudo systemctl enable medora
```

## 7. Verify
Check logs:
```bash
sudo journalctl -u medora -f
```
