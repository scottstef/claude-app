# app/database.py
import sqlite3
import json
import uuid
from contextlib import contextmanager
from flask import session
from app.config import Config

@contextmanager
def get_db():
    """Get database connection with context manager"""
    conn = sqlite3.connect(str(Config.DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize the database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_type TEXT DEFAULT 'text'
            )
        ''')
        
        # NEW: Add a table to track database changes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS db_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                last_backup_hash TEXT,
                last_backup_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
    print(f"Database initialized: {Config.DATABASE_PATH}")

def get_session_id():
    """Get or create a session ID for the user"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

def save_message_to_db(session_id, role, content, message_type='text'):
    """Save a message to the database"""
    with get_db() as conn:
        cursor = conn.cursor()
        # Convert content to JSON string if it's a complex object
        if isinstance(content, (dict, list)):
            content_str = json.dumps(content)
        else:
            content_str = str(content)
        
        cursor.execute('''
            INSERT INTO conversations (session_id, role, content, message_type)
            VALUES (?, ?, ?, ?)
        ''', (session_id, role, content_str, message_type))
        conn.commit()

def get_conversation_history(session_id, limit=50):
    """Get conversation history from database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT role, content, message_type, created_at
            FROM conversations
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (session_id, limit))
        
        rows = cursor.fetchall()
        
        # Convert to the format expected by Claude API
        messages = []
        for row in reversed(rows):  # Reverse to get chronological order
            try:
                # Try to parse JSON content
                content = json.loads(row['content'])
            except:
                # If not JSON, keep as string
                content = row['content']
            
            messages.append({
                'role': row['role'],
                'content': content
            })
        
        return messages

def clear_conversation_history(session_id):
    """Clear conversation history for a session"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM conversations WHERE session_id = ?', (session_id,))
        conn.commit()