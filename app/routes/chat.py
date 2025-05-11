# app/routes/chat.py
from flask import Blueprint, request, jsonify
from anthropic import Anthropic
from app.config import Config
from app.database import get_session_id, save_message_to_db, get_conversation_history
import requests
import base64
import os

chat_bp = Blueprint('chat', __name__)
client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

def handle_github_command(message):
    """Handle GitHub-specific commands"""
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        return None
    
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # Simple command parsing
    if "list my repos" in message.lower():
        response = requests.get('https://api.github.com/user/repos', headers=headers)
        if response.status_code == 200:
            repos = response.json()
            repo_list = "\n".join([f"- {repo['name']}: {repo['description'] or 'No description'}" for repo in repos[:10]])
            return f"Here are your recent repositories:\n{repo_list}"
    
    elif "show file" in message.lower():
        # Try to extract repo and file path
        # Format: "show file app.py from claude-app repo"
        parts = message.lower().split()
        if "from" in parts and "repo" in parts:
            try:
                file_idx = parts.index("file") + 1
                from_idx = parts.index("from")
                repo_idx = parts.index("repo")
                
                filename = parts[file_idx]
                repo_name = parts[from_idx + 1]
                
                url = f'https://api.github.com/repos/scottstef/{repo_name}/contents/{filename}'
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    file_data = response.json()
                    content = base64.b64decode(file_data['content']).decode('utf-8')
                    return f"File: {filename} from {repo_name}\n\n```{content}```"
            except:
                pass
    
    return None

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
        # Check for GitHub commands
        github_response = handle_github_command(message)
        if github_response:
            # Pass GitHub data to Claude for discussion
            message = f"{github_response}\n\nUser's question: {message}"
        
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

@chat_bp.route('/get_history', methods=['GET'])
def get_chat_history():
    """Endpoint to retrieve conversation history for the current session"""
    try:
        # Get the current session ID
        session_id = get_session_id()
        
        # Retrieve history from database
        history = get_conversation_history(session_id)
        
        return jsonify({
            'history': history,
            'conversation_length': len(history)
        })
        
    except Exception as e:
        print(f"Error in get_history endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500