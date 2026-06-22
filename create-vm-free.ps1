# create-vm-free.ps1 - CREATE FREE TIER VM IN WESTUS2 (FIXED IMAGE)
Write-Host "=== CREATING FREE TIER AZURE VM (westus2) ===" -ForegroundColor Cyan

# ============================================================
# CONFIGURATION - USING westus2 AS REQUESTED
# ============================================================
$LOCATION = "westus2"          # Washington, USA
$RG = "rg-marketing-agents"
$VM_NAME = "marketing-agent-vm"
$VM_SIZE = "Standard_B2ats_v2"   # FREE tier (2 vCPUs, 1 GB RAM)
$ADMIN_USER = "azureuser"
# FIXED: Using explicit URN instead of the 'UbuntuLTS' alias
$IMAGE = "Canonical:0001-com-ubuntu-server-jammy:22_04-lts:latest"

# ============================================================
# 1. LOGIN
# ============================================================
Write-Host "[1] Logging in..." -ForegroundColor Yellow
az login

# ============================================================
# 2. CREATE RESOURCE GROUP
# ============================================================
Write-Host "[2] Creating Resource Group in $LOCATION..." -ForegroundColor Yellow
az group create --name $RG --location $LOCATION

# ============================================================
# 3. CREATE VM (FREE TIER - B2ats_v2) WITH EXPLICIT URN
# ============================================================
Write-Host "[3] Creating VM ($VM_SIZE) with image: $IMAGE..." -ForegroundColor Yellow
Write-Host "This will take 2-3 minutes..." -ForegroundColor Gray

az vm create `
    --resource-group $RG `
    --name $VM_NAME `
    --location $LOCATION `
    --image $IMAGE `
    --size $VM_SIZE `
    --admin-username $ADMIN_USER `
    --generate-ssh-keys `
    --public-ip-sku Standard

# Check if VM creation succeeded
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ VM creation failed. Trying fallback image..." -ForegroundColor Red
    
    # Fallback to Ubuntu 20.04 LTS if 22.04 fails
    $IMAGE_FALLBACK = "Canonical:UbuntuServer:20_04-lts:latest"
    Write-Host "Trying fallback image: $IMAGE_FALLBACK" -ForegroundColor Yellow
    
    az vm create `
        --resource-group $RG `
        --name $VM_NAME `
        --location $LOCATION `
        --image $IMAGE_FALLBACK `
        --size $VM_SIZE `
        --admin-username $ADMIN_USER `
        --generate-ssh-keys `
        --public-ip-sku Standard
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ VM creation failed completely." -ForegroundColor Red
        Write-Host "💡 Try manually creating the VM in the Azure Portal." -ForegroundColor Yellow
        exit 1
    }
}

# ============================================================
# 4. OPEN PORTS (for your FastAPI app)
# ============================================================
Write-Host "[4] Opening ports..." -ForegroundColor Yellow

# Open HTTP (80), HTTPS (443), and your app port (8000)
az vm open-port --resource-group $RG --name $VM_NAME --port 80 --priority 100
az vm open-port --resource-group $RG --name $VM_NAME --port 443 --priority 110
az vm open-port --resource-group $RG --name $VM_NAME --port 8000 --priority 120

# ============================================================
# 5. GET PUBLIC IP
# ============================================================
Write-Host "[5] Getting public IP address..." -ForegroundColor Yellow
$PUBLIC_IP = az vm list-ip-addresses `
    --resource-group $RG `
    --name $VM_NAME `
    --query "[].virtualMachine.network.publicIpAddresses[0].ipAddress" `
    --output tsv

if (-not $PUBLIC_IP) {
    Write-Host "❌ Failed to retrieve public IP." -ForegroundColor Red
    exit 1
}

# ============================================================
# 6. OUTPUT
# ============================================================
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " ✅ VM CREATED SUCCESSFULLY! " -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "VM Details:" -ForegroundColor Yellow
Write-Host "  Name:      $VM_NAME" -ForegroundColor White
Write-Host "  Size:      $VM_SIZE (FREE tier)" -ForegroundColor White
Write-Host "  Region:    $LOCATION (Washington, USA)" -ForegroundColor White
Write-Host "  Username:  $ADMIN_USER" -ForegroundColor White
Write-Host "  IP:        $PUBLIC_IP" -ForegroundColor Cyan
Write-Host ""
Write-Host "SSH Command:" -ForegroundColor Yellow
Write-Host "  ssh $ADMIN_USER@$PUBLIC_IP" -ForegroundColor Green
Write-Host ""
Write-Host "API URL (once your app is running):" -ForegroundColor Yellow
Write-Host "  http://$PUBLIC_IP`:8000" -ForegroundColor Green
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. SSH into your VM:" -ForegroundColor White
Write-Host "   ssh $ADMIN_USER@$PUBLIC_IP" -ForegroundColor Green
Write-Host ""
Write-Host "2. Run the setup script to deploy your marketing agents:" -ForegroundColor White
Write-Host "   On the VM, create setup-vm.sh and run it" -ForegroundColor Green
Write-Host ""
Write-Host "3. Or copy files directly using SCP:" -ForegroundColor White
Write-Host "   scp -r ./app ${ADMIN_USER}@${PUBLIC_IP}:~/app" -ForegroundColor Green
Write-Host ""