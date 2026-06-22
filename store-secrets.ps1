# store-secrets.ps1
$RESOURCE_GROUP = "rg-marketing-agents"
$PROJECT_NAME = "magentic"

Write-Host "🔐 Storing secrets in Azure Key Vault..." -ForegroundColor Yellow

$KV_NAME = "${PROJECT_NAME}kv"

# Get the Key Vault URI
$KV_URI = az keyvault show --name $KV_NAME --resource-group $RESOURCE_GROUP --query "properties.vaultUri" --output tsv
Write-Host "✅ Key Vault URI: $KV_URI" -ForegroundColor Green

Write-Host ""
Write-Host "📋 Please enter your API keys below:" -ForegroundColor Cyan

# Foundry API Key
$FOUNDRY_KEY = Read-Host -Prompt "Enter your Foundry API Key"
if ($FOUNDRY_KEY -and $FOUNDRY_KEY -ne "") {
    az keyvault secret set --vault-name $KV_NAME --name "foundry-api-key" --value $FOUNDRY_KEY
}

# Google Ads Token
$GOOGLE_TOKEN = Read-Host -Prompt "Enter your Google Ads Developer Token"
if ($GOOGLE_TOKEN -and $GOOGLE_TOKEN -ne "") {
    az keyvault secret set --vault-name $KV_NAME --name "google-ads-token" --value $GOOGLE_TOKEN
}

# Meta Token
$META_TOKEN = Read-Host -Prompt "Enter your Meta Access Token"
if ($META_TOKEN -and $META_TOKEN -ne "") {
    az keyvault secret set --vault-name $KV_NAME --name "meta-token" --value $META_TOKEN
}

# Replicate Token (Optional)
$REPLICATE_TOKEN = Read-Host -Prompt "Enter your Replicate API Token (optional, press Enter to skip)"
if ($REPLICATE_TOKEN -and $REPLICATE_TOKEN -ne "") {
    az keyvault secret set --vault-name $KV_NAME --name "replicate-token" --value $REPLICATE_TOKEN
}

Write-Host ""
Write-Host "✅ All secrets stored successfully in $KV_NAME!" -ForegroundColor Green