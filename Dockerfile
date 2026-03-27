# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir sqlalchemy==2.0.25
RUN pip install --no-cache-dir psycopg2-binary==2.9.9
RUN pip install --no-cache-dir requests==2.31.0
RUN pip install --no-cache-dir feedparser==6.0.11
RUN pip install --no-cache-dir beautifulsoup4==4.12.3
RUN pip install --no-cache-dir lxml==5.1.0
RUN pip install --no-cache-dir anthropic==0.18.1
RUN pip install --no-cache-dir python-dotenv==1.0.1
RUN pip install --no-cache-dir APScheduler==3.10.4
RUN pip install --no-cache-dir numpy==1.26.4
RUN pip install --no-cache-dir scikit-learn==1.4.0
RUN pip install --no-cache-dir spacy==3.7.4

# Download spaCy model directly from pip
RUN pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/es_core_news_lg-3.7.0/es_core_news_lg-3.7.0-py3-none-any.whl

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the scheduler (shell form, NOT JSON array)
CMD python -m neurodiario.scheduler.auto_scheduler
