# app/cloud_storage.py
import hashlib
import subprocess
from datetime import datetime
from app.config import Config
from app.database import get_db

def get_database_hash():
    """Calculate SHA256 hash of the database file"""
    if not Config.DATABASE_PATH.exists():
        return None
    
    sha256_hash = hashlib.sha256()
    with open(Config.DATABASE_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def has_database_changed():
    """Check if database has changed since last backup"""
    current_hash = get_database_hash()
    if not current_hash:
        return False
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT last_backup_hash FROM db_metadata ORDER BY id DESC LIMIT 1')
        result = cursor.fetchone()
        
        if not result or result['last_backup_hash'] != current_hash:
            return True
    return False

def update_backup_metadata(db_hash=None):
    """Update the backup metadata with new hash"""
    if db_hash is None:
        db_hash = get_database_hash()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO db_metadata (last_backup_hash)
            VALUES (?)
        ''', (db_hash,))
        conn.commit()

def upload_database():
    """Upload database to Cloud Storage with change detection"""
    if not Config.GCS_BUCKET_NAME:
        print("GCS_BUCKET_NAME not set. Skipping database upload.")
        return False
    
    if not has_database_changed():
        print("Database unchanged since last backup. Skipping upload.")
        return False
    
    # Get current hash before upload
    current_hash = get_database_hash()
    
    # Upload to Cloud Storage
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    try:
        # Upload current database
        subprocess.run([
            'gsutil', 'cp', str(Config.DATABASE_PATH),
            f'gs://{Config.GCS_BUCKET_NAME}/chat_history.db'
        ], check=True)
        
        # Upload timestamped backup
        subprocess.run([
            'gsutil', 'cp', str(Config.DATABASE_PATH),
            f'gs://{Config.GCS_BUCKET_NAME}/backups/chat_history_{timestamp}.db'
        ], check=True)
        
        # Update metadata on successful upload
        update_backup_metadata(current_hash)
        print(f"Database backed up successfully at {timestamp}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error uploading database: {e}")
        return False

def download_database():
    """Download database from Cloud Storage"""
    if not Config.GCS_BUCKET_NAME:
        print("GCS_BUCKET_NAME not set. Skipping database download.")
        return False
    
    try:
        subprocess.run([
            'gsutil', 'cp',
            f'gs://{Config.GCS_BUCKET_NAME}/chat_history.db',
            str(Config.DATABASE_PATH)
        ], check=True)
        
        print("Database downloaded successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        if 'No URLs matched' not in str(e):
            print(f"Error downloading database: {e}")
        else:
            print("No existing database found in Cloud Storage. Starting fresh.")
        return False