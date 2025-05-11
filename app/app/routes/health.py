# app/routes/health.py
from flask import Blueprint, jsonify
from app.database import get_db
from app.config import Config

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for container monitoring"""
    try:
        # Test database connection
        with get_db() as conn:
            conn.execute('SELECT 1')
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'uploads_dir': Config.UPLOADS_DIR.exists(),
            'data_dir': Config.DATA_DIR.exists()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@health_bp.route('/test', methods=['GET'])
def test():
    """Test route to verify the API is working"""
    from anthropic import Anthropic
    from app.config import Config
    
    try:
        client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
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