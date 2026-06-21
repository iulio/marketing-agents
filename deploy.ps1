# deploy-europe.ps1 - One-click Azure Deployment (European Region)
Write-Host "🚀 Starting deployment of Agentic Marketing System in Europe..." -ForegroundColor Cyan

# ============================================================
# 🇪🇺 REGION CONFIGURATION - CHANGE THIS TO YOUR PREFERRED EUROPEAN REGION
# ============================================================
# Popular options:
#   westeurope      (Netherlands) - Best overall availability
#   northeurope     (Ireland)     - Great for UK/Ireland proximity
#   germanywestcentral (Frankfurt) - Great for Central Europe/Finance
#   francecentral   (Paris)       - Great for France/Southern Europe
#   swedencentral   (Sweden)      - Best for sustainability/carbon neutral
#   italynorth      (Milan)       - Good for Southern Europe
#   spaincentral    (Madrid)      - Newer region, good for Iberia
# ============================================================
$LOCATION = "westeurope"   # <-- CHANGE THIS TO YOUR PREFERRED REGION

# Project naming (must be globally unique for some resources)
$RESOURCE_GROUP = "rg-marketing-agents"
$PROJECT_NAME = "marketing-agents"

Write-Host "📍 Target Region: $LOCATION" -ForegroundColor Yellow

# ============================================================
# 1. Azure Login
# ============================================================
Write-Host "🔐 Logging into Azure..." -ForegroundColor Yellow
az login

# Optional: Set default subscription if you have multiple
# az account set --subscription "YOUR_SUBSCRIPTION_ID"

# ============================================================
# 2. Create Resource Group in Europe
# ============================================================
Write-Host "🏗️ Creating Resource Group in $LOCATION..." -ForegroundColor Yellow
az group create --name $RESOURCE_GROUP --location $LOCATION

# ============================================================
# 3. Deploy Infrastructure via Bicep (using European region)
# ============================================================
Write-Host "🏗️ Deploying infrastructure (Bicep) to $LOCATION..." -ForegroundColor Yellow
az deployment group create `
    --resource-group $RESOURCE_GROUP `
    --template-file infra/main.bicep `
    --parameters projectName=$PROJECT_NAME location=$LOCATION

# ============================================================
# 4. Build and Push Docker Image to Azure Container Registry
# ============================================================
Write-Host "🐳 Building and pushing Docker image to ACR..." -ForegroundColor Yellow
$ACR_NAME = "${PROJECT_NAME}acr"
$APP_NAME = "${PROJECT_NAME}-app"
$IMAGE_TAG = "latest"

# Build the image remotely in Azure (faster, no Docker Desktop needed)
az acr build `
    --registry $ACR_NAME `
    --image ${APP_NAME}:${IMAGE_TAG} `
    --file Dockerfile .

# ============================================================
# 5. Deploy the Container App (or update existing)
# ============================================================
Write-Host "☁️ Deploying container app to $LOCATION..." -ForegroundColor Yellow
$IMAGE = "${ACR_NAME}.azurecr.io/${APP_NAME}:${IMAGE_TAG}"

az containerapp update `
    --name $APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --image $IMAGE

# ============================================================
# 6. Get the App URL
# ============================================================
$URL = az containerapp show `
    --name $APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --query properties.configuration.ingress.fqdn `
    --output tsv

# ============================================================
# 7. Output Summary
# ============================================================
Write-Host ""
Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "🌐 Your app is available at: https://$URL" -ForegroundColor Cyan
Write-Host "📍 Region: $LOCATION" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Yellow
Write-Host "1. Configure your Google Ads and Meta API tokens in Azure Key Vault"
Write-Host "   Run: .\store-secrets.ps1  (if you have the script)"
Write-Host "   Or manually:"
Write-Host "   az keyvault secret set --vault-name ${PROJECT_NAME}-kv --name 'foundry-api-key' --value 'YOUR_KEY'"
Write-Host ""
Write-Host "2. Access your dashboard at: https://$URL"
Write-Host "3. Start onboarding clients!"
Write-Host ""