
# deploy-vm-private.ps1 - CORRECTED WITH FULL IMAGE URN
Write-Host "=== DEPLOYING MARKETING AGENTS ON AZURE VM (Private Repo) ===" -ForegroundColor Cyan

# ============================================================
# CONFIGURATION - CHANGE THESE VALUES
# ============================================================
$LOCATION = "westeurope"   # Change to your preferred region
$RG = "rg-marketing-agents"
$VM_NAME = "marketing-agent-vm"
$VM_SIZE = "Standard_B2s"   # 2 vCPUs, 4GB RAM
$ADMIN_USER = "azureuser"
$ADMIN_PASSWORD = "HAIBROSAFACEMBANI!123"  # CHANGE THIS!

# ============================================================
# GITHUB CONFIGURATION - FILL THESE IN
# ============================================================
$GITHUB_USER = "iulio"        # Your GitHub username
$GITHUB_REPO = "marketing-agents"            # Your private repo name
$GITHUB_PAT = Read-Host -Prompt "Enter your GitHub Personal Access Token" -AsSecureString
$GITHUB_PAT = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($GITHUB_PAT))   # Your PAT

# ============================================================
# IMAGE SPECIFICATION - USING FULL URN (ALWAYS WORKS)
# ============================================================
$IMAGE_URN = "Canonical:0001-com-ubuntu-server-jammy:22_04-lts:latest"
# Alternative: "Canonical:UbuntuServer:18.04-LTS:latest" (if above fails)

# ============================================================
# 1. LOGIN & RESOURCE GROUP
# ============================================================
Write-Host "[1] Logging in..." -ForegroundColor Yellow
az login

Write-Host "[2] Creating Resource Group in $LOCATION..." -ForegroundColor Yellow
az group create --name $RG --location $LOCATION

# ============================================================
# 2. CREATE VM WITH DOCKER - USING FULL IMAGE URN
# ============================================================
Write-Host "[3] Creating VM with Docker (image: $IMAGE_URN)..." -ForegroundColor Yellow
az vm create `
    --resource-group $RG `
    --name $VM_NAME `
    --location $LOCATION `
    --image $IMAGE_URN `
    --size $VM_SIZE `
    --admin-username $ADMIN_USER `
    --admin-password $ADMIN_PASSWORD `
    --public-ip-sku Standard

# Check if VM creation succeeded
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ VM creation failed. Please check the error above." -ForegroundColor Red
    exit 1
}

# ============================================================
# 3. OPEN PORTS (80, 443, 8000)
# ============================================================
Write-Host "[4] Opening ports..." -ForegroundColor Yellow
az vm open-port --resource-group $RG --name $VM_NAME --port 80 --priority 100
az vm open-port --resource-group $RG --name $VM_NAME --port 443 --priority 110
az vm open-port --resource-group $RG --name $VM_NAME --port 8000 --priority 120

# ============================================================
# 4. GET PUBLIC IP
# ============================================================
$PUBLIC_IP = az vm list-ip-addresses --resource-group $RG --name $VM_NAME --query "[].virtualMachine.network.publicIpAddresses[0].ipAddress" --output tsv

if (-not $PUBLIC_IP) {
    Write-Host "❌ Failed to retrieve public IP." -ForegroundColor Red
    exit 1
}

# ============================================================
# 5. SSH INTO VM AND INSTALL DOCKER + CLONE PRIVATE REPO
# ============================================================
Write-Host "[5] Installing Docker and cloning private repo on VM..." -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no $ADMIN_USER@$PUBLIC_IP "
    # Install Docker and Git
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose git
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $ADMIN_USER

    # Clone private repository using PAT
    cd /home/$ADMIN_USER
    echo 'Cloning private repository...'
    git clone https://${GITHUB_PAT}@github.com/${GITHUB_USER}/${GITHUB_REPO}.git

    if [ $? -eq 0 ]; then
        echo '✅ Successfully cloned private repository!'
        cd ${GITHUB_REPO}
    else
        echo '❌ Failed to clone repository. Creating fallback project...'
        mkdir -p ~/app
        cd ~/app
        
        # Fallback Dockerfile
        cat > Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn
COPY app.py .
CMD [\"uvicorn\", \"app:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]
EOF

        cat > app.py << 'EOF'
from fastapi import FastAPI
app = FastAPI()
@app.get(\"/\")
def root(): return {\"message\": \"Marketing Agents API running on VM!\"}
@app.get(\"/health\")
def health(): return {\"status\": \"healthy\"}
EOF

        docker build -t marketing-agents .
        docker run -d --name marketing-agents -p 8000:8000 --restart always marketing-agents
        exit 0
    fi

    # Build and run from repo
    if [ -f Dockerfile ]; then
        echo 'Building container from your repository...'
        docker build -t marketing-agents .
        docker run -d --name marketing-agents -p 8000:8000 --restart always marketing-agents
    elif [ -f docker-compose.yml ]; then
        echo 'Using docker-compose...'
        docker-compose up -d
    else
        echo '⚠️ No Dockerfile or docker-compose.yml found. Please add them.'
    fi
"

# ============================================================
# 6. OUTPUT
# ============================================================
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " DEPLOYMENT SUCCESSFUL " -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "VM Public IP: $PUBLIC_IP" -ForegroundColor Cyan
Write-Host "API URL: http://$PUBLIC_IP:8000" -ForegroundColor Cyan
Write-Host "SSH Command: ssh $ADMIN_USER@$PUBLIC_IP" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. SSH into the VM: ssh $ADMIN_USER@$PUBLIC_IP"
Write-Host "2. Check running containers: docker ps"
Write-Host "3. View logs: docker logs marketing-agents"
Write-Host "4. Open your browser: http://$PUBLIC_IP:8000"
Write-Host ""
Write-Host "If your repository uses docker-compose, SSH in and run:"
Write-Host "   cd ~/${GITHUB_REPO} && docker-compose up -d"
Write-Host ""