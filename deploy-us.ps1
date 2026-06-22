# deploy-usa.ps1 - ULTIMATE FALLBACK (US East)
Write-Host "=== AZURE MARKETING AGENTS DEPLOYMENT (US East) ===" -ForegroundColor Cyan

# ============================================================
# CONFIGURATION - THIS REGION WORKS FOR 99% OF STUDENT SUBS
# ============================================================
$LOCATION = "eastus"   # Virginia, USA (closest to Europe in the US)
$RG = "rg-marketing-agents"
$PROJECT = "marketingagents"

$ACR_NAME = "${PROJECT}acr"
$APP_NAME = "${PROJECT}app"
$ENV_NAME = "${PROJECT}env"
$KV_NAME = "${PROJECT}kv"
$FOUNDRY_NAME = "${PROJECT}foundry"
$LOGS_NAME = "${PROJECT}logs"
$IDENTITY_NAME = "${PROJECT}id"

Write-Host "Using region: $LOCATION (US East - Virginia)" -ForegroundColor Yellow

# Stop on ANY error from now on
$ErrorActionPreference = "Stop"

# ============================================================
# 1. LOGIN & REGISTER PROVIDERS
# ============================================================
Write-Host "[1] Logging in..." -ForegroundColor Yellow
az login

Write-Host "[2] Registering providers..." -ForegroundColor Yellow
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.ContainerRegistry --wait
az provider register --namespace Microsoft.KeyVault --wait
az provider register --namespace Microsoft.CognitiveServices --wait
az provider register --namespace Microsoft.OperationalInsights --wait
Write-Host "[OK] Providers registered." -ForegroundColor Green

# ============================================================
# 2. RESOURCE GROUP
# ============================================================
Write-Host "[3] Creating Resource Group in $LOCATION..." -ForegroundColor Yellow
az group create --name $RG --location $LOCATION

# ============================================================
# 3. MANAGED IDENTITY
# ============================================================
Write-Host "[4] Creating Managed Identity..." -ForegroundColor Yellow
az identity create --name $IDENTITY_NAME --resource-group $RG --location $LOCATION
$IDENTITY_ID = az identity show --name $IDENTITY_NAME --resource-group $RG --query id --output tsv
$IDENTITY_PRINCIPAL = az identity show --name $IDENTITY_NAME --resource-group $RG --query principalId --output tsv
Write-Host "[OK] Managed Identity created." -ForegroundColor Green

# ============================================================
# 4. KEY VAULT
# ============================================================
Write-Host "[5] Creating Key Vault..." -ForegroundColor Yellow
az keyvault create --name $KV_NAME --resource-group $RG --location $LOCATION --sku standard
az keyvault set-policy --name $KV_NAME --object-id $IDENTITY_PRINCIPAL --secret-permissions get list set
$VAULT_URI = az keyvault show --name $KV_NAME --resource-group $RG --query properties.vaultUri --output tsv
Write-Host "[OK] Key Vault created." -ForegroundColor Green

# ============================================================
# 5. CONTAINER REGISTRY
# ============================================================
Write-Host "[6] Creating Container Registry..." -ForegroundColor Yellow
az acr create --name $ACR_NAME --resource-group $RG --location $LOCATION --sku Basic --admin-enabled true
$ACR_LOGIN = az acr show --name $ACR_NAME --resource-group $RG --query loginServer --output tsv
Write-Host "[OK] Container Registry created." -ForegroundColor Green

# ============================================================
# 6. AI FOUNDRY
# ============================================================
Write-Host "[7] Creating AI Foundry..." -ForegroundColor Yellow
az cognitiveservices account create `
    --name $FOUNDRY_NAME `
    --resource-group $RG `
    --location $LOCATION `
    --kind AIServices `
    --sku S0
$FOUNDRY_ENDPOINT = az cognitiveservices account show --name $FOUNDRY_NAME --resource-group $RG --query properties.endpoint --output tsv
Write-Host "[OK] AI Foundry created." -ForegroundColor Green

# ============================================================
# 7. LOG ANALYTICS
# ============================================================
Write-Host "[8] Creating Log Analytics..." -ForegroundColor Yellow
az monitor log-analytics workspace create --name $LOGS_NAME --resource-group $RG --location $LOCATION
$LOG_WORKSPACE_RESOURCE_ID = az monitor log-analytics workspace show --name $LOGS_NAME --resource-group $RG --query id --output tsv
$LOG_KEY = az monitor log-analytics workspace get-shared-keys --name $LOGS_NAME --resource-group $RG --query primarySharedKey --output tsv
Write-Host "[OK] Log Analytics created." -ForegroundColor Green

# ============================================================
# 8. CONTAINER APPS ENVIRONMENT
# ============================================================
Write-Host "[9] Creating Container Apps Environment..." -ForegroundColor Yellow
az containerapp env create `
    --name $ENV_NAME `
    --resource-group $RG `
    --location $LOCATION `
    --logs-workspace-id $LOG_WORKSPACE_RESOURCE_ID `
    --logs-workspace-key $LOG_KEY
Write-Host "[OK] Container Apps Environment created." -ForegroundColor Green

# ============================================================
# 9. BUILD & PUSH DOCKER IMAGE
# ============================================================
Write-Host "[10] Building and pushing Docker image to ACR..." -ForegroundColor Yellow
az acr build --registry $ACR_NAME --image ${APP_NAME}:latest --file Dockerfile .
Write-Host "[OK] Docker image built and pushed." -ForegroundColor Green

# ============================================================
# 10. DEPLOY CONTAINER APP
# ============================================================
Write-Host "[11] Deploying Container App..." -ForegroundColor Yellow
$IMAGE_FULL = "${ACR_LOGIN}/${APP_NAME}:latest"

az containerapp create `
    --name $APP_NAME `
    --resource-group $RG `
    --environment $ENV_NAME `
    --image $IMAGE_FULL `
    --target-port 8000 `
    --ingress external `
    --cpu 2.0 `
    --memory 4Gi `
    --min-replicas 0 `
    --max-replicas 5 `
    --env-vars `
        AZURE_AI_PROJECT_ENDPOINT=$FOUNDRY_ENDPOINT `
        KEY_VAULT_URI=$VAULT_URI `
        LLM_MODE=foundry
Write-Host "[OK] Container App created." -ForegroundColor Green

# ============================================================
# 11. ASSIGN MANAGED IDENTITY TO CONTAINER APP
# ============================================================
Write-Host "[12] Assigning Managed Identity to Container App..." -ForegroundColor Yellow
az containerapp identity assign --name $APP_NAME --resource-group $RG --user-assigned $IDENTITY_ID
Write-Host "[OK] Identity assigned." -ForegroundColor Green

# ============================================================
# 12. GET URL
# ============================================================
$URL = az containerapp show --name $APP_NAME --resource-group $RG --query properties.configuration.ingress.fqdn --output tsv

# ============================================================
# OUTPUT
# ============================================================
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " DEPLOYMENT SUCCESSFUL " -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "URL: https://$URL" -ForegroundColor Cyan
Write-Host "Resource Group: $RG" -ForegroundColor Cyan
Write-Host "Region: $LOCATION (US East - Virginia)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Add your Foundry API Key to Key Vault:"
Write-Host "   az keyvault secret set --vault-name $KV_NAME --name 'foundry-api-key' --value 'YOUR_KEY'"
Write-Host ""
Write-Host "2. Add Google Ads and Meta tokens:"
Write-Host "   az keyvault secret set --vault-name $KV_NAME --name 'google-ads-token' --value 'YOUR_TOKEN'"
Write-Host "   az keyvault secret set --vault-name $KV_NAME --name 'meta-token' --value 'YOUR_TOKEN'"
Write-Host ""
Write-Host "3. Open your dashboard at: https://$URL"
Write-Host ""