#Dockerfile
FROM ghcr.io/scottstef/claude-base:latest

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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

# Expose port
EXPOSE 5000

# Command to run the application
CMD ["/app/scripts/start.sh"]


## Build and Push Instructions
# docker build -t your-repo/base-image:tag -f Dockerfile.base .
# docker push your-repo/base-image:tag