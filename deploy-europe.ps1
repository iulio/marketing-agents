# deploy-europe.ps1 - One-click Azure Deployment (European Region)
Write-Host "[START] Starting deployment of Agentic Marketing System in Europe..." -ForegroundColor Cyan

# ============================================================
# EUROPEAN REGION CONFIGURATION - CHANGE THIS TO YOUR PREFERRED REGION
# ============================================================
$LOCATION = "westeurope"   # Amsterdam - best for Romania

# ============================================================
# PROJECT NAMING (Must be globally unique for some resources)
# ============================================================
$RESOURCE_GROUP = "rg-marketing-agents"
$PROJECT_NAME = "magentic"           # No hyphens! (for ACR compatibility)
$APP_NAME = "magentic-app"

# ============================================================
# 1. Azure Login
# ============================================================
Write-Host "[LOGIN] Logging into Azure..." -ForegroundColor Yellow
az login

# ============================================================
# 2. Register Required Azure Providers
# ============================================================
Write-Host "[REGISTER] Registering required Azure providers..." -ForegroundColor Yellow
az provider register -n Microsoft.App --wait
az provider register -n Microsoft.ContainerRegistry --wait
az provider register -n Microsoft.KeyVault --wait
az provider register -n Microsoft.CognitiveServices --wait
az provider register -n Microsoft.OperationalInsights --wait
az provider register -n Microsoft.ManagedIdentity --wait
Write-Host "[OK] All providers registered successfully." -ForegroundColor Green

# ============================================================
# 3. Create Resource Group in Europe
# ============================================================
Write-Host "[DEPLOY] Creating Resource Group in $LOCATION..." -ForegroundColor Yellow
az group create --name $RESOURCE_GROUP --location $LOCATION

# ============================================================
# 4. Build and Push Docker Image to Azure Container Registry (First)
# ============================================================
Write-Host "[DOCKER] Creating Azure Container Registry..." -ForegroundColor Yellow
$ACR_NAME = "${PROJECT_NAME}acr"   # e.g., magenticacr (alphanumeric only)
az acr create --name $ACR_NAME --resource-group $RESOURCE_GROUP --sku Basic --location $LOCATION

Write-Host "[DOCKER] Building and pushing Docker image to ACR..." -ForegroundColor Yellow
$IMAGE_TAG = "latest"
$FULL_IMAGE_NAME = "${ACR_NAME}.azurecr.io/${APP_NAME}:${IMAGE_TAG}"

# Build the image remotely in Azure (faster, no Docker Desktop needed)
az acr build `
    --registry $ACR_NAME `
    --image ${APP_NAME}:${IMAGE_TAG} `
    --file Dockerfile .

# ============================================================
# 5. Get ACR Admin Credentials (for Container App deployment)
# ============================================================
Write-Host "[CREDENTIALS] Retrieving ACR credentials..." -ForegroundColor Yellow
$ACR_PASSWORD = az acr credential show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query "passwords[0].value" --output tsv
$ACR_USERNAME = $ACR_NAME

# ============================================================
# 6. Deploy Infrastructure via Bicep (using European region)
# ============================================================
Write-Host "[DEPLOY] Deploying infrastructure (Bicep) to $LOCATION..." -ForegroundColor Yellow
az deployment group create `
    --resource-group $RESOURCE_GROUP `
    --template-file infra/main.bicep `
    --parameters location=$LOCATION projectName=$PROJECT_NAME appName=$APP_NAME acrName=$ACR_NAME acrPassword=$ACR_PASSWORD

# ============================================================
# 7. Get the App URL
# ============================================================
$URL = az containerapp show `
    --name $APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --query properties.configuration.ingress.fqdn `
    --output tsv

# ============================================================
# 8. Output Summary
# ============================================================
Write-Host ""
Write-Host "[OK] Deployment complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "[URL] Your app is available at: https://$URL" -ForegroundColor Cyan
Write-Host "[REGION] Region: $LOCATION" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[NEXT] Next steps:" -ForegroundColor Yellow
Write-Host "1. Configure your secrets in Azure Key Vault:"
Write-Host "   Run: .\store-secrets.ps1"
Write-Host ""
Write-Host "2. Access your dashboard at: https://$URL"
Write-Host "3. Start onboarding clients!"
Write-Host ""