FROM python:3.11-slim

LABEL maintainer="royki"
LABEL description="Ethereum TPS Load Generator"

# Set working directory
WORKDIR /app

# Unbuffer Python output for Docker logs
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY src/ ./src/

# Create directory for keystores
RUN mkdir -p /app/keystores

# Expose metrics port
EXPOSE 9000

# Default to server mode, can be overridden
CMD ["python3", "app.py", "--server"]

