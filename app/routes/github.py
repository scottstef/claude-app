# app/routes/github.py
from flask import Blueprint, request, jsonify
import requests
import os
import base64

github_bp = Blueprint('github', __name__)

def get_github_headers():
    """Get headers for GitHub API requests"""
    token = os.environ.get('GITHUB_TOKEN')
    return {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

@github_bp.route('/github/repos', methods=['GET'])
def list_repos():
    """List user's GitHub repositories"""
    headers = get_github_headers()
    response = requests.get('https://api.github.com/user/repos', headers=headers)
    return jsonify(response.json())

@github_bp.route('/github/file', methods=['POST'])
def get_file_content():
    """Get content of a specific file"""
    data = request.get_json()
    owner = data.get('owner', 'scottstef')  # Default to your username
    repo = data.get('repo')
    path = data.get('path')
    
    headers = get_github_headers()
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        file_data = response.json()
        # Decode base64 content
        content = base64.b64decode(file_data['content']).decode('utf-8')
        return jsonify({
            'content': content,
            'path': path,
            'repo': repo,
            'size': file_data.get('size'),
            'url': file_data.get('html_url')
        })
    
    return jsonify({'error': 'File not found', 'status': response.status_code}), 404