from flask import Flask, render_template, request, jsonify, send_from_directory, session
import os
from anthropic import Anthropic
from werkzeug.utils import secure_filename
import base64
import mimetypes
from datetime import datetime
from dotenv import load_dotenv
# NEW: Import for SQLite and sessions
import uuid
import sqlite3
import json

load_dotenv()

# Get API key
api_key = os.environ.get("ANTHROPIC_API_KEY")

# Debug output
print(f"Full API key: '{api_key}'")
print(f"API key type: {type(api_key)}")
print(f"API key first 20 chars: '{api_key[:20]}'")
print(f"API key last 20 chars: '...{api_key[-20:]}'")

# Check for any whitespace
import json
print(f"API key as JSON: {json.dumps(api_key)}")

# Manually test the API key
try:
    test_client = Anthropic(api_key=api_key.strip())
    print("Test client created with stripped API key! ")
except Exception as e:
    print(f"Error creating test client: {e}")

app = Flask(__name__)
# NEW: Configure session with a secret key
app.secret_key = os.environ.get('SECRET_KEY', str(uuid.uuid4()))
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

if api_key:
    client = Anthropic(api_key=api_key)
    print("\nClient initialized successfully!")

# Test the client with a simple request
    try:
        test_response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hello"}]
        )
        print("Client test successful!")
    except Exception as e:
        print(f"Client test failed: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\nERROR: Cannot initialize Anthropic client - no API key")

# NEW: SQLite database setup
DATABASE = 'chat_history.db'

def init_db():
    """Initialize the database"""
    with sqlite3.connect(DATABASE) as conn:
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
        conn.commit()
    print(f"Database initialized: {DATABASE}")

# Initialize database when app starts
init_db()

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

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

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'json', 'py', 'js', 'html', 'css', 'md', 'docx', 'doc'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def encode_file_for_claude(file_path):
    """Encode file for Claude API based on file type"""
    import mimetypes
    mime_type, _ = mimetypes.guess_type(file_path)
    file_ext = os.path.splitext(file_path)[1].lower()
    
    with open(file_path, 'rb') as file:
        # Handle Word documents
        if file_ext in ('.docx', '.doc'):
            try:
                from docx import Document
                document = Document(file_path)
                full_text = []
                for para in document.paragraphs:
                    full_text.append(para.text)
                return {
                    "type": "text",
                    "text": "\n".join(full_text)
                }
            except Exception as e:
                print(f"Error reading Word document: {e}")
                return {
                    "type": "text",
                    "text": f"Error reading Word document: {e}\n\nUnable to process the file content."
                }
        
        # Handle PDF files
        elif file_ext == '.pdf':
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return {
                    "type": "text",
                    "text": text
                }
            except Exception as e:
                print(f"Error reading PDF file: {e}")
                return {
                    "type": "text",
                    "text": f"Error reading PDF file: {e}\n\nUnable to process the file content."
                }
        
        # Handle images
        elif mime_type and mime_type.startswith('image/'):
            # For images, encode as base64
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": base64.b64encode(file.read()).decode()
                }
            }
        else:
            # For text files, read as text
            try:
                file.seek(0)
                return {
                    "type": "text",
                    "text": file.read().decode('utf-8')
                }
            except UnicodeDecodeError:
                return {
                    "type": "text",
                    "text": "This file appears to be a binary file that cannot be processed as text."
                }

@app.route('/')
def index():
    return render_template('index.html')

# NEW: Routes for conversation history
@app.route('/clear_history', methods=['POST'])
def clear_history():
    """Clear the conversation history"""
    session_id = get_session_id()
    clear_conversation_history(session_id)
    return jsonify({'success': True, 'message': 'Conversation history cleared'})

@app.route('/get_history', methods=['GET'])
def get_history():
    """Get the current conversation history"""
    session_id = get_session_id()
    history = get_conversation_history(session_id)
    return jsonify({
        'success': True,
        'history': history,
        'count': len(history)
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    # Get message from request and session ID
    message = request.form.get('message', '')
    session_id = get_session_id()
    
    # Make file upload optional
    file_content = None
    filename = None
    
    if 'file' in request.files and request.files['file'].filename != '':
        file = request.files['file']
        
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                file_ext = os.path.splitext(filename)[1].lower()
                print(f"Processing file: {filename} (type: {file_ext})")
                
                file_content = encode_file_for_claude(filepath)
                
            except Exception as e:
                print(f"Error processing file: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': f'Error processing file: {str(e)}'}), 500
        else:
            return jsonify({'error': 'Invalid file type. Supported types include: txt, pdf, docx, doc, images, etc.'}), 400
    
    if not message and not file_content:
        return jsonify({'error': 'Please provide either a message or a file'}), 400
    
    try:
        # System message
        system_message = """You are a helpful assistant that analyzes files and answers questions. 

        IMPORTANT: When you provide code modifications or updates, ALWAYS:
        1. Comment where you make changes with markers like "# NEW", "# CHANGED", or "# UPDATED"
        2. If the change is substantial, include a brief comment explaining what was changed
        3. Make it easy for the user to spot the differences from the original code
        """
        
        # Build content array based on what's provided
        content = []
        
        if message:
            content.append({
                "type": "text",
                "text": message
            })
        
        if file_content:
            content.append(file_content)
        
        if not file_content and message and ("file" in message.lower() or "analyze" in message.lower()):
            content.append({
                "type": "text",
                "text": "Note: No file was uploaded for analysis."
            })
        
        # CHANGED: Get history from database
        messages = get_conversation_history(session_id)
        
        user_message = {
            "role": "user",
            "content": content if len(content) > 1 else message
        }
        messages.append(user_message)
        
        # Send to Claude
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=4096,
            system=system_message,
            messages=messages
        )
        
        # CHANGED: Save to database
        save_message_to_db(session_id, 'user', content if len(content) > 1 else message)
        save_message_to_db(session_id, 'assistant', response.content[0].text)
        
        # Update count for response
        history_count = len(get_conversation_history(session_id))
        
        response_data = {
            'success': True,
            'analysis': response.content[0].text,
            'filename': filename if filename else None,
            'has_file': file_content is not None,
            'conversation_length': history_count
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in upload route: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Chat endpoint with conversation history"""
    try:
        print("=== Chat endpoint called ===")
        
        data = request.get_json()
        message = data.get('message', '')
        session_id = get_session_id()
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
        
        print(f"Received message: {message}")
        
        # System message
        system_message = """You are a helpful assistant that analyzes files and answers questions. 

        IMPORTANT: When you provide code modifications or updates, ALWAYS:
        1. Comment where you make changes with markers like "# NEW", "# CHANGED", or "# UPDATED"
        2. If the change is substantial, include a brief comment explaining what was changed
        3. Make it easy for the user to spot the differences from the original code
        """
        
        # CHANGED: Get history from database
        messages = get_conversation_history(session_id)
        
        user_message = {
            "role": "user",
            "content": message
        }
        messages.append(user_message)
        
        # Create the API request
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=4096,
            system=system_message,
            messages=messages
        )
        
        # CHANGED: Save to database
        save_message_to_db(session_id, 'user', message)
        save_message_to_db(session_id, 'assistant', response.content[0].text)
        
        # Update count for response
        history_count = len(get_conversation_history(session_id))
        
        print(f"Response received successfully")
        
        return jsonify({
            'response': response.content[0].text,
            'conversation_length': history_count
        })
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/test', methods=['GET'])
def test():
    """Test route to verify the API is working"""
    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": "Say hello!"
            }]
        )
        return jsonify({
            'success': True,
            'response': response.content[0].text
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/admin/sessions', methods=['GET'])
def list_sessions():
    """List all active sessions"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT session_id, COUNT(*) as message_count, 
                   MIN(created_at) as first_message,
                   MAX(created_at) as last_message
            FROM conversations
            GROUP BY session_id
            ORDER BY last_message DESC
        ''')
        sessions = cursor.fetchall()
    
    return jsonify({
        'success': True,
        'sessions': [dict(session) for session in sessions]
    })
    
if __name__ == '__main__':
    app.run(debug=True, port=5000)