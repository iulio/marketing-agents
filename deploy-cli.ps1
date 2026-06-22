# deploy-cli.ps1 - AZURE CLI ONLY (No Bicep)
Write-Host "=== AZURE MARKETING AGENTS DEPLOYMENT ===" -ForegroundColor Cyan

# ============================================================
# CONFIGURATION
# ============================================================
$LOCATION = "norwayeast"
$RG = "rg-marketing-agents"
$PROJECT = "marketingagents"

$ACR_NAME = "${PROJECT}acr"
$APP_NAME = "${PROJECT}app"
$ENV_NAME = "${PROJECT}env"
$KV_NAME = "${PROJECT}kv"
$FOUNDRY_NAME = "${PROJECT}foundry"
$LOGS_NAME = "${PROJECT}logs"
$IDENTITY_NAME = "${PROJECT}id"

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
Write-Host "[3] Creating Resource Group..." -ForegroundColor Yellow
az group create --name $RG --location $LOCATION

# ============================================================
# 3. MANAGED IDENTITY
# ============================================================
Write-Host "[4] Creating Managed Identity..." -ForegroundColor Yellow
az identity create --name $IDENTITY_NAME --resource-group $RG --location $LOCATION
$IDENTITY_ID = az identity show --name $IDENTITY_NAME --resource-group $RG --query id --output tsv
$IDENTITY_PRINCIPAL = az identity show --name $IDENTITY_NAME --resource-group $RG --query principalId --output tsv

# ============================================================
# 4. KEY VAULT
# ============================================================
Write-Host "[5] Creating Key Vault..." -ForegroundColor Yellow
az keyvault create --name $KV_NAME --resource-group $RG --location $LOCATION --sku standard
az keyvault set-policy --name $KV_NAME --object-id $IDENTITY_PRINCIPAL --secret-permissions get list set
$VAULT_URI = az keyvault show --name $KV_NAME --resource-group $RG --query properties.vaultUri --output tsv

# ============================================================
# 5. CONTAINER REGISTRY
# ============================================================
Write-Host "[6] Creating Container Registry..." -ForegroundColor Yellow
az acr create --name $ACR_NAME --resource-group $RG --location $LOCATION --sku Basic --admin-enabled true
$ACR_LOGIN = az acr show --name $ACR_NAME --resource-group $RG --query loginServer --output tsv

# ============================================================
# 6. AI FOUNDRY
# ============================================================
Write-Host "[7] Creating AI Foundry..." -ForegroundColor Yellow
az cognitiveservices account create `
    --name $FOUNDRY_NAME `
    --resource-group $RG `
    --location $LOCATION `
    --kind AIServices `
    --sku S0 `
    --custom-subdomain $FOUNDRY_NAME
$FOUNDRY_ENDPOINT = az cognitiveservices account show --name $FOUNDRY_NAME --resource-group $RG --query properties.endpoint --output tsv

# ============================================================
# 7. LOG ANALYTICS
# ============================================================
Write-Host "[8] Creating Log Analytics..." -ForegroundColor Yellow
az monitor log-analytics workspace create --name $LOGS_NAME --resource-group $RG --location $LOCATION
$LOG_CUSTOMER_ID = az monitor log-analytics workspace show --name $LOGS_NAME --resource-group $RG --query customerId --output tsv

# ============================================================
# 8. CONTAINER APPS ENVIRONMENT
# ============================================================
Write-Host "[9] Creating Container Apps Environment..." -ForegroundColor Yellow
az containerapp env create `
    --name $ENV_NAME `
    --resource-group $RG `
    --location $LOCATION `
    --logs-workspace-id $LOG_CUSTOMER_ID
$ENV_ID = az containerapp env show --name $ENV_NAME --resource-group $RG --query id --output tsv

# ============================================================
# 9. BUILD & PUSH DOCKER IMAGE
# ============================================================
Write-Host "[10] Building and pushing Docker image..." -ForegroundColor Yellow
az acr build --registry $ACR_NAME --image ${APP_NAME}:latest --file Dockerfile .

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
    --identity $IDENTITY_ID `
    --env-vars `
        AZURE_AI_PROJECT_ENDPOINT=$FOUNDRY_ENDPOINT `
        KEY_VAULT_URI=$VAULT_URI `
        LLM_MODE=foundry

# ============================================================
# 11. GET URL
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
Write-Host "Region: $LOCATION" -ForegroundColor Cyan
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