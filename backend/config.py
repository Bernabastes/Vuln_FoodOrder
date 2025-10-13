import os
from datetime import timedelta


class Config:
    # Database Configuration
    DATABASE_PATH = os.environ.get('DATABASE_PATH', '/app/vulneats.db')
    DATABASE_URL = os.environ.get('DATABASE_URL')  # For PostgreSQL in production
    
    # Security Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'vulneats-secret-key-change-in-production')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    
    # Application Configuration
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/app/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # JWT Configuration
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block'
    }
    
    # Payment Configuration
    CHAPA_SECRET_KEY = os.environ.get('CHAPA_SECRET_KEY')
    CHAPA_PUBLIC_KEY = os.environ.get('CHAPA_PUBLIC_KEY')
    
    # Cloudinary Configuration
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')
    CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')
    
    # URL Configuration
    FRONTEND_BASE_URL = os.environ.get('FRONTEND_BASE_URL', 'http://localhost:3000')
    BACKEND_BASE_URL = os.environ.get('BACKEND_BASE_URL', 'http://localhost:5001')
    
    # Production-specific settings
    @property
    def is_production(self):
        return self.FLASK_ENV == 'production'
    
    @property
    def use_postgres(self):
        return bool(self.DATABASE_URL)


class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = 'development'


class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = 'production'
    
    # Production security settings
    @property
    def session_cookie_secure(self):
        return True
    
    @property
    def session_cookie_httponly(self):
        return True
    
    @property
    def session_cookie_samesite(self):
        return 'Lax'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}