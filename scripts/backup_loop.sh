# scripts/backup_loop.sh
#!/bin/bash

# Continuous backup with change detection
while true; do
    echo "Checking if database has changed..."
    if curl -s http://localhost:5000/admin/db_status | grep -q '"has_changes":true'; then
        echo "Database has changed. Starting backup..."
        curl -X POST http://localhost:5000/admin/backup_db
    else
        echo "No changes detected. Skipping backup."
    fi
    
    # Wait 5 minutes before next check
    sleep 300
done