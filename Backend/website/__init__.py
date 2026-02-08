from flask import Flask, url_for, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager
from flask_migrate import Migrate
from datetime import timedelta

db = SQLAlchemy()
migrate = Migrate()
DB_NAME = "database.db"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY']= 'FreestyleBijch'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    
    # Add session security settings
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to cookies
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # Session expires after 24 hours (increased from 1 hour)
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
    app.config['SESSION_REFRESH_EACH_REQUEST'] = True  # Refresh session with each request
    app.config['SESSION_COOKIE_PATH'] = '/'  # Apply cookie to entire domain
    
    # Remember me cookie settings
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)  # Remember for 30 days
    app.config['REMEMBER_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['REMEMBER_COOKIE_REFRESH_EACH_REQUEST'] = True
    
    # Ensure session is not domain-specific to work across different ports
    app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow sessions across any domains/ports
    
    # Add response headers for all responses
    @app.after_request
    def add_security_headers(response):
        # Don't set no-cache headers on the remember token cookie
        if 'Set-Cookie' in response.headers and 'remember_token' in response.headers['Set-Cookie']:
            return response
            
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    # Add session validation middleware
    @app.before_request
    def validate_session():
        # Skip validation for login and static routes
        if request.path.startswith('/static') or request.path == '/login' or request.path == '/logout':
            return None
            
        # Check if user is authenticated through flask-login, but session may be invalid
        from flask_login import current_user
        from flask import session, redirect, url_for, flash
        
        if not current_user.is_anonymous:
            # If user is logged in but session might be corrupted
            if '_user_id' not in session:
                print("WARNING: User authenticated but session missing _user_id")
                from flask_login import logout_user
                logout_user()
                flash('Your session has expired. Please log in again.', 'error')
                return redirect(url_for('auth.login', next=request.path))
                
            # For API routes, return JSON response instead of redirect for session errors
            if request.path.startswith('/api/') and not current_user.is_authenticated:
                from flask import jsonify
                response = jsonify({'success': False, 'message': 'Session expired, please login again'})
                response.status_code = 401
                return response
        
        return None
    
    db.init_app(app)
    
    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    
    # Import all models to ensure Flask-Migrate detects them
    from .models import User, Note, Course, Category, Lesson, Achievement, PasswordReset, EmailVerification
    
    # Initialize Flask-Migrate after importing all models
    migrate.init_app(app, db)
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))
    
    # Add a diagnostic route to show all registered routes
    @app.route('/routes')
    def list_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'route': str(rule)
            })
        return jsonify(routes)
        
    return app