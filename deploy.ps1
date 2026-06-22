# deploy.ps1 - One-click Azure deployment
Write-Host "🚀 Starting deployment of Agentic Marketing System..." -ForegroundColor Cyan

# Variables - CHANGE THESE
$RESOURCE_GROUP = "rg-marketing-agents"
$LOCATION = "eastnorway"
$PROJECT_NAME = "marketing-agents"

# Login to Azure
az login

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Deploy infrastructure via Bicep
Write-Host "🏗️ Deploying infrastructure..." -ForegroundColor Yellow
az deployment group create `
    --resource-group $RESOURCE_GROUP `
    --template-file infra/main.bicep `
    --parameters projectName=$PROJECT_NAME

# Build and push Docker image
Write-Host "🐳 Building and pushing Docker image..." -ForegroundColor Yellow
$ACR_NAME = "${PROJECT_NAME}acr"
$APP_NAME = "${PROJECT_NAME}-app"
az acr build `
    --registry $ACR_NAME `
    --image ${APP_NAME}:latest `
    --file Dockerfile .

# Deploy the container app
Write-Host "☁️ Deploying container app..." -ForegroundColor Yellow
$IMAGE = "${ACR_NAME}.azurecr.io/${APP_NAME}:latest"
az containerapp update `
    --name $APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --image $IMAGE

# Get the app URL
$URL = az containerapp show `
    --name $APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --query properties.configuration.ingress.fqdn `
    --output tsv

Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host "🌐 Your app is available at: https://$URL" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Next steps:"
Write-Host "1. Configure your Google Ads and Meta API tokens in Azure Key Vault"
Write-Host "2. Access your dashboard at https://$URL"
Write-Host "3. Start onboarding clients!"