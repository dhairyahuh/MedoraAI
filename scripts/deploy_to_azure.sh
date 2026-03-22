#!/bin/bash
set -e

echo "========================================================"
echo "       Medora AI - Azure Deployment Script              "
echo "========================================================"

# Check if logged in
az account show > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ You must run 'az login' first."
    exit 1
fi

# Variables
RESOURCE_GROUP="MedoraResources"
LOCATION="eastus"
RAND_STR=$(openssl rand -hex 3)
ACR_NAME="medora$RAND_STR"
APP_NAME="medora-app-$RAND_STR"
PLAN_NAME="MedoraPlan"

echo "Using Random Suffix: $RAND_STR"
echo "Resource Group: $RESOURCE_GROUP"
echo "ACR Name: $ACR_NAME"
echo "App Name: $APP_NAME"
echo ""

# 1. Create Resource Group
echo "Creating Resource Group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# 2. Update .gitignore (temporary) to exclude local models if too big for build context
# (Dockerignore usually handles this, we rely on .dockerignore if we had one. We'll rely on ACR build ignoring gitignore files if configured, or just uploading what is there.)
# Note: az acr build respects .dockerignore

# 3. Create ACR
echo "Creating Container Registry (ACR)..."
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true

# 4. Build Image
echo "Building Docker Image in Azure Cloud (this takes ~10 mins)..."
az acr build --registry $ACR_NAME --image medora-ai:latest .

# 5. Create App Service Plan
echo "Creating App Service Plan (B1 Linux)..."
az appservice plan create --name $PLAN_NAME --resource-group $RESOURCE_GROUP --is-linux --sku B1

# 6. Create Web App
echo "Creating Web App..."
az webapp create --resource-group $RESOURCE_GROUP --plan $PLAN_NAME --name $APP_NAME --deployment-container-image-name $ACR_NAME.azurecr.io/medora-ai:latest

# 7. Configure App
echo "Configuring App Settings..."
ACR_PASS=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)
ACR_USER=$(az acr credential show --name $ACR_NAME --query "username" -o tsv)

az webapp config container set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --docker-custom-image-name $ACR_NAME.azurecr.io/medora-ai:latest \
    --docker-registry-server-url https://$ACR_NAME.azurecr.io \
    --docker-registry-server-user $ACR_USER \
    --docker-registry-server-password $ACR_PASS

az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --settings WEBSITES_PORT=8000 PORT=8000 SCM_DO_BUILD_DURING_DEPLOYMENT=true

echo ""
echo "========================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "URL: https://$APP_NAME.azurewebsites.net"
echo "========================================================"
echo "Note: The first load may take 2-3 minutes while models download."
