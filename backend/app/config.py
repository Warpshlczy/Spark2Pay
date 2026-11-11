"""
Application Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""

    # Paths
    BASE_DIR = Path(__file__).parent.parent

    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR}/spark2pay.db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Application
    PORT = int(os.getenv('PORT', 3038))
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Session
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    SESSION_COOKIE_SECURE = not DEBUG
    PERMANENT_SESSION_LIFETIME = int(os.getenv('SESSION_LIFETIME', 2592000))  # 30 days

    # File Upload
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_UPLOAD_SIZE', 16777216))  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'svg'}

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')

    # API Keys (Optional)
    FIXER_API_KEY = os.getenv('FIXER_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')
    GOOGLE_VISION_API_KEY = os.getenv('GOOGLE_VISION_API_KEY')

    # AI Engine
    # provider: 'auto' (OpenAI if key present, else heuristic), 'openai', 'gemini',
    # 'ollama', or 'heuristic' (deterministic built-in engine, no network)
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'auto')
    AI_MODEL = os.getenv('AI_MODEL', 'gpt-4o-mini')
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    OPENAI_BASE_URL = os.getenv(
        'OPENAI_BASE_URL', 'https://api.openai.com/v1'
    )
    GEMINI_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/openai'

    # PayPal Execution Layer
    # mode: 'sandbox' (real PayPal sandbox APIs) or 'simulation'
    # (deterministic local simulator, no credentials needed)
    PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'simulation')
    PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')
    PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET')
    PAYPAL_WEBHOOK_ID = os.getenv('PAYPAL_WEBHOOK_ID')
    PAYPAL_SANDBOX_BASE = 'https://api-m.sandbox.paypal.com'
    PAYPAL_LIVE_BASE = 'https://api-m.paypal.com'

    # Public URLs used to build PayPal return/cancel links and approve pages
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')

    # SMTP (Optional)
    SMTP_HOST = os.getenv('SMTP_HOST')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    SMTP_FROM_EMAIL = os.getenv('SMTP_FROM_EMAIL')
    SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'True').lower() == 'true'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
