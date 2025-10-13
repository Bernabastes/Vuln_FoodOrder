import os
from datetime import timedelta

class Config:
    # Database configuration
    DATABASE_PATH = 'vulneats.db'
    
    # Flask configuration
    SECRET_KEY = 'vulneats-secret-key-change-in-production'  # VULNERABLE: Weak secret key
    DEBUG = True
    
    # File upload configuration
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # JWT configuration (if using JWT)
    JWT_SECRET_KEY = 'jwt-secret-key-change-in-production'  # VULNERABLE: Weak JWT secret
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # Security headers (will be implemented later)
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block'
    }
