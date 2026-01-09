import os
import secrets
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    # ==========================================================================
    # Core Settings
    # ==========================================================================
    
    # Secret key - CRITICAL for session security
    # Will generate a random one if not set, but this should be set in production!
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    # Environment
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'
    
    # ==========================================================================
    # Database
    # ==========================================================================
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Check connection before using
        'pool_recycle': 300,    # Recycle connections after 5 minutes
    }
    
    # ==========================================================================
    # Security Settings
    # ==========================================================================
    
    # Session cookies
    SESSION_COOKIE_SECURE = FLASK_ENV == 'production'  # HTTPS only in production
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Brute force protection
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_BLOCK_DURATION = 900  # 15 minutes in seconds
    
    # File upload limits
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max upload
    
    # WTF Forms (CSRF)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # ==========================================================================
    # External Services
    # ==========================================================================
    
    WA_API_URL = os.environ.get('WA_API_URL', 'http://wabot:3000')
    
    # Google Drive
    GOOGLE_DRIVE_ROOT_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_ROOT_FOLDER_ID')
    GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
    GOOGLE_OAUTH_REFRESH_TOKEN = os.environ.get('GOOGLE_OAUTH_REFRESH_TOKEN')
    
    # ==========================================================================
    # Validation
    # ==========================================================================
    
    @staticmethod
    def validate():
        """Validate required configuration. Call on app startup."""
        errors = []
        
        if not os.environ.get('SECRET_KEY'):
            print("⚠️  WARNING: SECRET_KEY not set! Using generated key (not recommended for production)")
        
        if not os.environ.get('DATABASE_URL'):
            errors.append("DATABASE_URL is required")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")