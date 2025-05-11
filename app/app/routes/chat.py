# app/routes/chat.py
from flask import Blueprint, request, jsonify
from anthropic import Anthropic
from app.config import Config
from app.database import get_session_id, save_message_to_db, get_conversation_history

chat_bp = Blueprint('chat', __name__)
client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

SYSTEM_MESSAGE = """You are a helpful assistant that analyzes files and answers questions. 

IMPORTANT: When you provide code modifications or updates, ALWAYS:
1. Comment where you make changes with markers like "# NEW", "# CHANGED", or "# UPDATED"
2. If the change is substantial, include a brief comment explaining what was changed
3. Make it easy for the user to spot the differences from the original code
"""

@chat_bp.route('/chat', methods=['POST'])
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
        
        # Get history from database
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
            system=SYSTEM_MESSAGE,
            messages=messages
        )
        
        # Save to database
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