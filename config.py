"""
Production configuration for Attendance Tracker
"""
import os
from datetime import timedelta

class Config:
    # Basic Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    
    # Database configuration
    if os.environ.get('DATABASE_URL'):
        # For PostgreSQL/MySQL (production)
        DATABASE_URL = os.environ.get('DATABASE_URL')
    else:
        # For SQLite (development/small production)
        DATABASE = os.environ.get('DATABASE_PATH') or 'attendance.db'
    
    # File upload configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'static/student_photos'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)  # 30 minutes for production
    
    # Security settings for production
    SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Logging configuration
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    
    # Face recognition settings
    FACE_RECOGNITION_ENABLED = os.environ.get('FACE_RECOGNITION_ENABLED', 'true').lower() == 'true'
    
    # File storage settings
    STATIC_FOLDER = 'static'
    TEMPLATES_FOLDER = 'templates'

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development

class ProductionConfig(Config):
    DEBUG = False
    
    # Production-specific settings
    if os.environ.get('DATABASE_URL'):
        # Use PostgreSQL/MySQL in production
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Additional security for production
    PREFERRED_URL_SCHEME = 'https'

class TestingConfig(Config):
    TESTING = True
    DATABASE = ':memory:'  # In-memory database for testing

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
