from flask import Flask, request
from flask_cors import CORS
from pymongo import MongoClient
from app.config import Config
import os

# MongoDB client (initialized lazily)
mongo_client = None
db = None


def get_db():
    """Get MongoDB database instance."""
    global mongo_client, db
    if db is None:
        mongo_client = MongoClient(Config.MONGODB_URI)
        # Use 'guruji' as the database name
        db = mongo_client['guruji']
    return db


def create_app():
    """Flask application factory."""
    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static'
    )
    
    # Load configuration
    app.config.from_object(Config)
    
    # Security settings
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') != 'development'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Enable CORS with restricted origins
    allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(',')
    CORS(app, origins=allowed_origins, supports_credentials=True)
    
    # Security headers middleware
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Don't cache sensitive API responses
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
        return response
    
    # Context processor to make config available in templates
    @app.context_processor
    def inject_config():
        return {'config': Config}
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.courses import courses_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.enrollments import enrollments_bp
    from app.routes.recordings import recordings_bp
    from app.routes.notes import notes_bp
    from app.routes.certificates import certificates_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    # Also register at /auth to support callback URLs configured without /api prefix
    app.register_blueprint(auth_bp, url_prefix='/auth', name='auth_external')
    app.register_blueprint(courses_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(enrollments_bp, url_prefix='/api')
    app.register_blueprint(recordings_bp, url_prefix='/api')
    app.register_blueprint(notes_bp)
    app.register_blueprint(certificates_bp)
    
    return app
