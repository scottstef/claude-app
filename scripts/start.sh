#!/bin/bash
# scripts/start.sh

echo "Starting Claude Chat Application on Cloud Run..."

# Create necessary directories in /tmp (writable in Cloud Run)
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

# Start Gunicorn server
echo "Starting Gunicorn application server..."
exec gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 2 \
    --worker-class gthread \
    --max-requests 1000 \
    --timeout 300 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    run:app