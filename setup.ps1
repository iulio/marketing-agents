# setup.ps1 - Complete Setup Script for Windows
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AGENTIC MARKETING AGENCY - SETUP" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ================================================================
# 1. CHECK ENVIRONMENT
# ================================================================
Write-Host "[1/8] Checking environment..." -ForegroundColor Yellow

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "WARNING: Not running as Administrator. Some features may not work." -ForegroundColor Yellow
}

# Check Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Docker not found. Please install Docker Desktop first." -ForegroundColor Red
    Write-Host "Download from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    exit 1
}

# ================================================================
# 2. CREATE PROJECT DIRECTORY
# ================================================================
Write-Host "[2/8] Setting up project..." -ForegroundColor Yellow
$PROJECT_DIR = "$env:USERPROFILE\marketing-agents"
if (-not (Test-Path $PROJECT_DIR)) {
    New-Item -ItemType Directory -Path $PROJECT_DIR -Force | Out-Null
    Write-Host "Created project directory: $PROJECT_DIR" -ForegroundColor Green
}
Set-Location $PROJECT_DIR

# ================================================================
# 3. CREATE APP STRUCTURE
# ================================================================
Write-Host "[3/8] Creating app structure..." -ForegroundColor Yellow

$DIRS = @("app", "app/static", "app/credentials", "data")
foreach ($dir in $DIRS) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# ================================================================
# 4. CREATE REQUIREMENTS.TXT
# ================================================================
Write-Host "[4/8] Creating requirements.txt..." -ForegroundColor Yellow
$requirements = @"
fastapi==0.115.6
uvicorn[standard]==0.34.0
gunicorn==23.0.0
langchain==0.3.13
langchain-community==0.3.13
langgraph==0.2.56
pydantic==2.10.4
python-dotenv==1.0.1
httpx==0.28.1
tenacity==9.0.0
redis==5.2.1
Pillow>=10.0.0
requests>=2.31.0
python-multipart==0.0.9
pyjwt==2.8.0
"@
$requirements | Out-File -FilePath "app\requirements.txt" -Encoding UTF8

Write-Host "requirements.txt created" -ForegroundColor Green

# ================================================================
# 5. CREATE DOCKERFILE
# ================================================================
Write-Host "[5/8] Creating Dockerfile..." -ForegroundColor Yellow
$dockerfile = @"
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

RUN mkdir -p /app/data

EXPOSE 8000

ENTRYPOINT ["gunicorn", "--config", "app/gunicorn.conf.py", "app.main:app"]
"@
$dockerfile | Out-File -FilePath "Dockerfile" -Encoding UTF8

Write-Host "Dockerfile created" -ForegroundColor Green

# ================================================================
# 6. INSTALL PYTHON DEPENDENCIES
# ================================================================
Write-Host "[6/8] Installing Python dependencies..." -ForegroundColor Yellow

# Check if Python is installed
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python not found. Please install Python 3.10+ first." -ForegroundColor Red
    exit 1
}

python -m pip install --upgrade pip
pip install -r app\requirements.txt

Write-Host "Python dependencies installed" -ForegroundColor Green

# ================================================================
# 7. BUILD DOCKER IMAGE
# ================================================================
Write-Host "[7/8] Building Docker image..." -ForegroundColor Yellow
docker build -t marketing-agents .

Write-Host "Docker image built" -ForegroundColor Green

# ================================================================
# 8. RUN DOCKER CONTAINER
# ================================================================
Write-Host "[8/8] Starting Docker container..." -ForegroundColor Yellow

# Stop existing container if running
docker stop marketing-agents 2>$null
docker rm marketing-agents 2>$null

docker run -d `
    -p 8000:8000 `
    --name marketing-agents `
    -v "$(pwd)\data:/app/data" `
    -e AUTO_OPTIMIZE=true `
    -e OPTIMIZATION_INTERVAL=60 `
    -e JWT_SECRET_KEY=your-secret-key-change-in-production `
    marketing-agents

Write-Host "Container started" -ForegroundColor Green

# ================================================================
# 9. GET IP AND URL
# ================================================================
$PUBLIC_IP = (Invoke-RestMethod -Uri "http://checkip.amazonaws.com" -ErrorAction SilentlyContinue) -replace "`n","" -replace "`r",""
if (-not $PUBLIC_IP) { $PUBLIC_IP = "localhost" }

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SETUP COMPLETE! " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Dashboard URL: http://${PUBLIC_IP}:8000" -ForegroundColor Green
Write-Host "Login: admin@agency.com" -ForegroundColor Green
Write-Host "Password: admin123" -ForegroundColor Green
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  View logs:        docker logs -f marketing-agents" -ForegroundColor White
Write-Host "  Stop container:   docker stop marketing-agents" -ForegroundColor White
Write-Host "  Restart:          docker restart marketing-agents" -ForegroundColor White
Write-Host "  Open in browser:  start http://localhost:8000" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan