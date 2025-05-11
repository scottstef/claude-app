# Build stage
FROM python:3.9-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies only in the builder stage
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    libxml2 \
    libxslt1.1 \
    curl \
    python3-pip \
    && pip install --no-cache-dir gsutil \
    && rm -rf /var/lib/apt/lists/*
    
# Add gcloud to PATH
ENV PATH $PATH:/usr/local/gcloud/google-cloud-sdk/bin

# Copy installed Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.9/site-packages/ /usr/local/lib/python3.9/site-packages/

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /tmp/uploads /tmp/data

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Copy scripts and make executable
COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.sh

# NEW: Remove unnecessary files
RUN find /app -type d -name "__pycache__" -exec rm -rf {} +
RUN find /app -name "*.pyc" -delete
RUN rm -rf /app/.git /app/tests /app/.pytest_cache 2>/dev/null || true

# Expose port
EXPOSE 5000

# Command to run the application
CMD ["/app/scripts/start.sh"]

