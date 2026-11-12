"""
Spark2Pay Backend Application Factory
Agentic subscription manager: AI savings advice executed through PayPal.
"""
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy
db = SQLAlchemy()

# Initialize Notification Scheduler (will be set up after app creation)
notification_scheduler = None


def create_app(config_name='default'):
    """
    Application factory pattern

    Args:
        config_name: Configuration to use (development, testing, production)

    Returns:
        Flask application instance
    """
    from app.config import config

    # Create Flask app
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)

    # Configure CORS
    CORS(app,
         supports_credentials=True,
         origins=app.config['CORS_ORIGINS'])

    # Initialize notification scheduler (only in production/development, not testing)
    if config_name != 'testing':
        from app.services.notification_scheduler import NotificationScheduler
        global notification_scheduler
        notification_scheduler = NotificationScheduler(app)

    # Register blueprints
    from app.api.v1 import api_v1
    app.register_blueprint(api_v1, url_prefix='/api/v1')

    # Runtime-editable settings (Settings UI overrides, persisted locally)
    with app.app_context():
        from app.services.runtime_config import init_runtime_config
        init_runtime_config(app)

    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'Spark2Pay API'}, 200

    @app.route('/')
    def index():
        return {
            'name': 'Spark2Pay API',
            'version': '1.0.0',
            'description': 'Agentic subscription manager - AI savings advice executed through PayPal',
            'endpoints': {
                'health': '/health',
                'api': '/api/v1',
                'docs': '/api/v1/status'
            }
        }, 200

    return app
