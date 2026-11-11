"""
API v1 Blueprint
"""
from flask import Blueprint

# Create API v1 blueprint
api_v1 = Blueprint('api_v1', __name__)

# Import and register sub-blueprints
from app.api.v1.auth import auth_bp
from app.api.v1.subscriptions import subscriptions_bp
from app.api.v1.budget import budget_bp
from app.api.v1.notifications import notifications_bp
from app.api.v1.household import household_bp
from app.api.v1.categories import categories_bp
from app.api.v1.payment_methods import payment_methods_bp
from app.api.v1.currencies import currencies_bp
from app.api.v1.statistics import statistics_bp
from app.api.v1.calendar import calendar_bp
from app.api.v1.ai import ai_bp
from app.api.v1.paypal import paypal_bp

api_v1.register_blueprint(auth_bp, url_prefix='/auth')
api_v1.register_blueprint(subscriptions_bp, url_prefix='/subscriptions')
api_v1.register_blueprint(budget_bp, url_prefix='/budget')
api_v1.register_blueprint(notifications_bp, url_prefix='/notifications')
api_v1.register_blueprint(household_bp, url_prefix='/household')
api_v1.register_blueprint(categories_bp, url_prefix='/categories')
api_v1.register_blueprint(payment_methods_bp, url_prefix='/payment-methods')
api_v1.register_blueprint(currencies_bp, url_prefix='/currencies')
api_v1.register_blueprint(statistics_bp, url_prefix='/statistics')
api_v1.register_blueprint(calendar_bp, url_prefix='/calendar')
api_v1.register_blueprint(ai_bp, url_prefix='/ai')
api_v1.register_blueprint(paypal_bp, url_prefix='/paypal')


@api_v1.route('/status')
def status():
    """API status endpoint"""
    return {
        'status': 'active',
        'version': 'v1',
        'message': 'Spark2Pay API v1 is running',
        'endpoints': {
            'auth': '/api/v1/auth/*',
            'subscriptions': '/api/v1/subscriptions',
            'budget': '/api/v1/budget',
            'notifications': '/api/v1/notifications',
            'household': '/api/v1/household',
            'categories': '/api/v1/categories',
            'payment_methods': '/api/v1/payment-methods',
            'currencies': '/api/v1/currencies',
            'statistics': '/api/v1/statistics',
            'calendar': '/api/v1/calendar',
            'ai': '/api/v1/ai/*',
            'paypal': '/api/v1/paypal/*'
        }
    }, 200
