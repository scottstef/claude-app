# scripts/download_db.sh
#!/bin/bash

# Check if bucket is configured
if [ -z "$GCS_BUCKET_NAME" ]; then
    echo "GCS_BUCKET_NAME not set. Skipping database download."
    exit 0
fi

# Download database from Cloud Storage
echo "Downloading database from gs://$GCS_BUCKET_NAME/chat_history.db..."
gsutil cp gs://$GCS_BUCKET_NAME/chat_history.db /app/data/chat_history.db 2>/dev/null || echo "No existing database found in Cloud Storage. Starting fresh."

# Set proper permissions
chmod 644 /app/data/chat_history.db