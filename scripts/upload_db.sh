# scripts/upload_db.sh
#!/bin/bash

# Check if bucket is configured
if [ -z "$GCS_BUCKET_NAME" ]; then
    echo "GCS_BUCKET_NAME not set. Skipping database upload."
    exit 0
fi

# Upload database to Cloud Storage
echo "Uploading database to gs://$GCS_BUCKET_NAME/"
if [ -f "/app/data/chat_history.db" ]; then
    # Create a timestamped backup
    timestamp=$(date +%Y%m%d_%H%M%S)
    gsutil cp /app/data/chat_history.db gs://$GCS_BUCKET_NAME/chat_history.db
    gsutil cp /app/data/chat_history.db gs://$GCS_BUCKET_NAME/backups/chat_history_${timestamp}.db
    echo "Database uploaded successfully"
else
    echo "Database file not found. Nothing to upload."
fi