# app/__init__.py
from flask import Flask, render_template
from app.config import Config
from app.database import init_db
from app.routes.chat import chat_bp
from app.routes.upload import upload_bp
from app.routes.admin import admin_bp
from app.routes.health import health_bp
from app.github import github_bp

def create_app():
    # Explicitly set template_folder relative to the app package
    app = Flask(__name__, 
                template_folder='../templates',  # Go up one level to find templates
                static_folder='../static')       # Same for static files if you have them
    
    app.config.from_object(Config)
    
    # Initialize directories
    Config.init_directories()
    
    # Initialize database
    init_db()
    
    # Register blueprints
    app.register_blueprint(chat_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(github_bp)

    # Root route
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app