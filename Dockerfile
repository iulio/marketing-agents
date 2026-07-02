FROM python:3.11-slim

WORKDIR /app

# Instalează dependințe de sistem
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiază și instalează dependințele Python
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiază codul aplicației
COPY app/ ./app/

# Creează directorul pentru date (dacă este necesar)
RUN mkdir -p /app/data
RUN playwright install chromium
RUN playwright install-deps
# Expune portul aplicației
EXPOSE 8000

# Rulează aplicația cu uvicorn
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]