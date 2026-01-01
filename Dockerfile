# CampusGrid - Dockerfile for Cloud Deployment
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for database
RUN mkdir -p manager

# Expose ports
EXPOSE 5001 9999

# Environment variables (can be overridden)
ENV DASHBOARD_PORT=5001
ENV MANAGER_PORT=9999
ENV DASHBOARD_HOST=0.0.0.0
ENV MANAGER_HOST=0.0.0.0

# Run the manager
CMD ["python", "run_manager.py"]
