# deploy-final.ps1 - THE ONE THAT ACTUALLY WORKS (FIXED)
Write-Host "=== DEPLOYMENT TO AZURE STARTING ===" -ForegroundColor Cyan

# ============================================================
# CONFIGURATION (CHANGE THESE IF NEEDED)
# ============================================================  Try westeurope if allowed, else northeurope/eastus
$RESOURCE_GROUP = "rg-marketing-agents"
$LOCATION = "norwayeast"
$PROJECT_NAME = "marketingagents" 

# ============================================================
# 1. LOGIN
# ============================================================
Write-Host "[LOGIN] Logging into Azure..." -ForegroundColor Yellow
az login

# ============================================================
# 2. REGISTER PROVIDERS (WITH PROPER WAIT)
# ============================================================
Write-Host "[REGISTER] Registering required providers..." -ForegroundColor Yellow
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.ContainerRegistry --wait
az provider register --namespace Microsoft.KeyVault --wait
az provider register --namespace Microsoft.CognitiveServices --wait
az provider register --namespace Microsoft.OperationalInsights --wait
Write-Host "[OK] Providers registered." -ForegroundColor Green

# ============================================================
# 3. CREATE RESOURCE GROUP
# ============================================================
Write-Host "[DEPLOY] Creating Resource Group in $LOCATION..." -ForegroundColor Yellow
az group create --name $RESOURCE_GROUP --location $LOCATION

# ============================================================
# 4. DEPLOY INFRASTRUCTURE (BICEP - SELF CONTAINED)
# ============================================================
Write-Host "[BICEP] Deploying infrastructure..." -ForegroundColor Yellow
az deployment group create `
    --resource-group $RESOURCE_GROUP `
    --template-file infra/main.bicep `
    --parameters projectName=$PROJECT_NAME location=$LOCATION

# ============================================================
# 5. GET ACR CREDENTIALS & BUILD IMAGE
# ============================================================
$ACR_NAME = "${PROJECT_NAME}acr"
$APP_NAME = "${PROJECT_NAME}app"
$IMAGE_NAME = "${APP_NAME}:latest"

Write-Host "[DOCKER] Building and pushing image to ACR..." -ForegroundColor Yellow
az acr build `
    --registry $ACR_NAME `
    --image $IMAGE_NAME `
    --file Dockerfile .

# ============================================================
# 6. UPDATE CONTAINER APP WITH NEW IMAGE
# ============================================================
$FULL_IMAGE = "${ACR_NAME}.azurecr.io/${IMAGE_NAME}"
Write-Host "[UPDATE] Updating container app..." -ForegroundColor Yellow
az containerapp update `
    --name $APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --image $FULL_IMAGE

# ============================================================
# 7. GET FINAL URL
# ============================================================
$URL = az containerapp show `
    --name $APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --query properties.configuration.ingress.fqdn `
    --output tsv

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " DEPLOYMENT SUCCESSFUL " -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "URL: https://$URL" -ForegroundColor Cyan
Write-Host "Resource Group: $RESOURCE_GROUP" -ForegroundColor Cyan
Write-Host "Region: $LOCATION" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Add your Foundry API Key to Key Vault:"
Write-Host "   az keyvault secret set --vault-name ${PROJECT_NAME}kv --name 'foundry-api-key' --value 'YOUR_KEY'"
Write-Host ""
Write-Host "2. Add Google Ads and Meta tokens:"
Write-Host "   az keyvault secret set --vault-name ${PROJECT_NAME}kv --name 'google-ads-token' --value 'YOUR_TOKEN'"
Write-Host "   az keyvault secret set --vault-name ${PROJECT_NAME}kv --name 'meta-token' --value 'YOUR_TOKEN'"
Write-Host ""
Write-Host "3. Open your dashboard at: https://$URL"
Write-Host ""