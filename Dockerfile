# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY infra/ ./infra/

# Expose the application port
EXPOSE 8000

# Run with Gunicorn
ENTRYPOINT ["gunicorn", "--config", "app/gunicorn.conf.py", "app.main:app"]