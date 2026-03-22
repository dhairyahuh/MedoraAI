#!/bin/bash
set -e

echo "========================================================"
echo "   Medora AI - Azure Deployment (Code Deploy)           "
echo "   * Use this if 'ContainerRegistry' is stuck *         "
echo "========================================================"

# Check login
az account show > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ You must run 'az login' first."
    exit 1
fi

# Variables
RESOURCE_GROUP=${RESOURCE_GROUP:-"MedoraResourcesCentral"}
LOCATION=${LOCATION:-"centralus"}  # 'centralus' is often allowed for students
RAND_STR=$(openssl rand -hex 3)
APP_NAME="medora-app-$RAND_STR"
PLAN_NAME="MedoraPlan"

echo "Using Random Suffix: $RAND_STR"
echo "Resource Group: $RESOURCE_GROUP"
echo "App Name: $APP_NAME"
echo ""

# 1. Create Resource Group
echo "Creating Resource Group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# 2. Create App Service Plan
echo "Creating App Service Plan (B1 Linux)..."
az appservice plan create --name $PLAN_NAME --resource-group $RESOURCE_GROUP --is-linux --sku B1

# 3. Create Web App
echo "Creating Web App..."
az webapp create --resource-group $RESOURCE_GROUP --plan $PLAN_NAME --name $APP_NAME --runtime "PYTHON:3.10"

# 4. Configure Startup Command
echo "Configuring Startup..."
# Chain commands: Download models -> Seed DB -> Start Server
STARTUP_CMD="python scripts/download_more_models.py && python scripts/check_and_seed_data.py && gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120"

az webapp config set --resource-group $RESOURCE_GROUP --name $APP_NAME --startup-file "$STARTUP_CMD"

# 5. Configure Settings
echo "Configuring Environment Variables..."
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $APP_NAME --settings \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true \
    PORT=8000 \
    WEBSITES_PORT=8000 \
    workers=2

# 6. Deploy Code
echo "Deploying Code (this takes ~5-10 mins)..."
# We archive the current directory (excluding ignore files) and upload
az webapp deployment source config-zip --resource-group $RESOURCE_GROUP --name $APP_NAME --src <(zip -r - . -x@.dockerignore)

echo ""
echo "========================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "URL: https://$APP_NAME.azurewebsites.net"
echo "========================================================"
