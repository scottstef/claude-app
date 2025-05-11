# app/routes/admin.py
from flask import Blueprint, jsonify
from app.database import clear_conversation_history, get_session_id, get_db
from app.cloud_storage import upload_database, download_database, has_database_changed

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/clear_history', methods=['POST'])
def clear_history():
    """Clear the conversation history"""
    session_id = get_session_id()
    clear_conversation_history(session_id)
    return jsonify({'success': True, 'message': 'Conversation history cleared'})

@admin_bp.route('/admin/get_history', methods=['GET'])
def get_history():
    """Get the current conversation history"""
    from app.database import get_conversation_history
    session_id = get_session_id()
    history = get_conversation_history(session_id)
    return jsonify({
        'success': True,
        'history': history,
        'count': len(history)
    })

@admin_bp.route('/admin/backup_db', methods=['POST'])
def backup_database():
    """Manually trigger database backup to Cloud Storage"""
    try:
        success = upload_database()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Database backed up successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Database backup failed or skipped (no changes)'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/admin/restore_db', methods=['POST'])
def restore_database():
    """Manually restore database from Cloud Storage"""
    try:
        success = download_database()
        
        if success:
            # Reinitialize database connection after restore
            from app.database import init_db
            init_db()
            return jsonify({
                'success': True,
                'message': 'Database restored successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Database restore failed'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/admin/sessions', methods=['GET'])
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

@admin_bp.route('/admin/db_status', methods=['GET'])
def db_status():
    """Check database status and backup information"""
    try:
        from app.cloud_storage import get_database_hash
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT last_backup_hash, last_backup_timestamp 
                FROM db_metadata 
                ORDER BY id DESC 
                LIMIT 1
            ''')
            backup_info = cursor.fetchone()
        
        current_hash = get_database_hash()
        changed = has_database_changed()
        
        return jsonify({
            'success': True,
            'current_hash': current_hash,
            'last_backup_hash': backup_info['last_backup_hash'] if backup_info else None,
            'last_backup_timestamp': backup_info['last_backup_timestamp'] if backup_info else None,
            'has_changes': changed
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500