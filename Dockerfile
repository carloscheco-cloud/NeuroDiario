# Use Python 3.11 slim image
FROM python:3.11-slim

# Force rebuild - 2026-03-27
# This comment forces Railway to rebuild and install sentence-transformers

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/es_core_news_lg-3.7.0/es_core_news_lg-3.7.0-py3-none-any.whl

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the scheduler
CMD ["python", "-m", "scheduler.auto_scheduler"]
