# app/routes/upload.py
from flask import Blueprint, request, jsonify
from anthropic import Anthropic
from app.config import Config
from app.database import get_session_id, save_message_to_db, get_conversation_history
from app.file_handler import allowed_file, save_uploaded_file, encode_file_for_claude

upload_bp = Blueprint('upload', __name__)
client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

SYSTEM_MESSAGE = """You are a helpful assistant that analyzes files and answers questions. 

IMPORTANT: When you provide code modifications or updates, ALWAYS:
1. Comment where you make changes with markers like "# NEW", "# CHANGED", or "# UPDATED"
2. If the change is substantial, include a brief comment explaining what was changed
3. Make it easy for the user to spot the differences from the original code
"""

@upload_bp.route('/upload', methods=['POST'])
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
            filename, filepath = save_uploaded_file(file)
            
            try:
                print(f"Processing file: {filename}")
                
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
        
        # Get history from database
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
            system=SYSTEM_MESSAGE,
            messages=messages
        )
        
        # Save to database
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