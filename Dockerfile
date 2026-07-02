FROM python:3.11-slim

WORKDIR /app

# Instalează dependințe de sistem necesare pentru compilare și browsere
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    libdbus-1-3 \
    libdrm2 \
    libx11-6 \
    libxcomposite1 \
    libxrandr2 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copiază și instalează dependințele Python
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiază codul aplicației
COPY app/ ./app/

# Creează directorul pentru date (dacă este necesar)
RUN mkdir -p /app/data

# Instalează browserele Playwright (am instalat manual dependențele de sistem mai sus)
RUN playwright install chromium

# Expune portul aplicației
EXPOSE 8000

# Rulează aplicația cu uvicorn
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
