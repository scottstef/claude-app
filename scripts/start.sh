#!/bin/bash
# scripts/start.sh

echo "Starting Claude Chat Application..."

# Create necessary directories
mkdir -p /tmp/data /tmp/uploads
chmod 755 /tmp/data /tmp/uploads

# Initialize Google Cloud CLI if credentials are available
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "Activating service account..."
    gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS || echo "Service account activation failed"
fi

# Download database from Cloud Storage on startup
if [ -n "$GCS_BUCKET_NAME" ]; then
    echo "Downloading database from gs://$GCS_BUCKET_NAME/"
    gsutil cp gs://$GCS_BUCKET_NAME/chat_history.db /tmp/data/chat_history.db 2>/dev/null || echo "No existing database found, starting fresh"
fi

# NEW: Graceful shutdown function
graceful_shutdown() {
    echo "Received shutdown signal. Backing up database..."
    
    if [ -n "$GCS_BUCKET_NAME" ]; then
        # Backup database before shutdown
        timestamp=$(date +%Y%m%d_%H%M%S)
        gsutil cp /tmp/data/chat_history.db gs://$GCS_BUCKET_NAME/chat_history.db
        gsutil cp /tmp/data/chat_history.db gs://$GCS_BUCKET_NAME/backups/chat_history_${timestamp}_shutdown.db
        echo "Database backed up successfully"
    fi
    
    # Gracefully terminate Gunicorn
    if [ -n "$GUNICORN_PID" ]; then
        echo "Terminating Gunicorn..."
        kill -TERM "$GUNICORN_PID" 2>/dev/null || echo "Failed to terminate Gunicorn"
    fi
    exit 0
}

# Set up signal handlers
trap graceful_shutdown SIGTERM SIGINT

# Start Gunicorn server
echo "Starting Gunicorn application server..."
gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 2 \
    --worker-class gthread \
    --max-requests 1000 \
    --timeout 300 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    run:app &

# Store Gunicorn PID for graceful shutdown
GUNICORN_PID=$!

# Wait for Gunicorn to finish
wait $GUNICORN_PID