import os
from datetime import timedelta


class Config:
    DATABASE_PATH = os.environ.get('DATABASE_PATH', '/app/vulneats.db')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'vulneats-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', '1') == '1'
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/app/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block'
    }


