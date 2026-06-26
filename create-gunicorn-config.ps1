Write-Host "Fixing missing gunicorn.conf.py..." -ForegroundColor Yellow

# Create the file
@"
# Gunicorn configuration for production
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
preload_app = True
"@ | Out-File -FilePath "app\gunicorn.conf.py" -Encoding UTF8

Write-Host "✅ gunicorn.conf.py created" -ForegroundColor Green

# Stop and remove old container
Write-Host "Stopping old container..." -ForegroundColor Yellow
docker stop marketing-agents 2>$null
docker rm marketing-agents 2>$null

# Rebuild
Write-Host "Rebuilding Docker image..." -ForegroundColor Yellow
docker build -t marketing-agents .

# Run new container
Write-Host "Starting new container..." -ForegroundColor Yellow
docker run -d -p 8000:8000 --name marketing-agents marketing-agents

# Check logs
Write-Host "Container started. Checking logs..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
docker logs marketing-agents

Write-Host ""
Write-Host "✅ Done! Access your dashboard at: http://localhost:8000" -ForegroundColor Green