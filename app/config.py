# app/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME')
    GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    # Paths
    BASE_DIR = Path('/app')
    DATA_DIR = BASE_DIR / 'data'
    UPLOADS_DIR = BASE_DIR / 'uploads'
    DATABASE_PATH = DATA_DIR / 'chat_history.db'
    
    # Flask settings
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32MB
    
    # File processing
    ALLOWED_EXTENSIONS = {
        'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 
        'csv', 'json', 'py', 'js', 'html', 'css', 
        'md', 'docx', 'doc'
    }
    
    # Backup settings
    BACKUP_INTERVAL_SECONDS = 300  # 5 minutes
    
    @staticmethod
    def init_directories():
        """Create necessary directories"""
        Config.DATA_DIR.mkdir(exist_ok=True)
        Config.UPLOADS_DIR.mkdir(exist_ok=True)