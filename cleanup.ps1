# cleanup.ps1 - COMPLETE RESOURCE DELETION SCRIPT
Write-Host "⚠️  WARNING: This will DELETE ALL resources created in the resource group 'rg-marketing-agents'!" -ForegroundColor Red
Write-Host "This includes Container Apps, Key Vault, Foundry, Container Registry, and all secrets." -ForegroundColor Red
Write-Host ""
$confirmation = Read-Host "Type 'YES' to confirm deletion"
if ($confirmation -ne "YES") {
    Write-Host "❌ Deletion cancelled." -ForegroundColor Yellow
    exit
}

# 1. Delete the Resource Group (This deletes EVERYTHING inside it)
Write-Host "🗑️ Deleting resource group: rg-marketing-agents..." -ForegroundColor Yellow
az group delete --name rg-marketing-agents --yes --no-wait

Write-Host "✅ Resource group deletion initiated. It may take a few minutes to complete." -ForegroundColor Green
Write-Host ""
Write-Host "📋 To check status, run: az group show --name rg-marketing-agents" -ForegroundColor Cyan