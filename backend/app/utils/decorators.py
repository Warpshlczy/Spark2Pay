"""
Authentication Decorators
"""
from functools import wraps
from flask import request, jsonify, current_app, g
from app.services.auth_service import AuthService
from app.models.user import User


def require_auth(f):
    """
    Decorator to require authentication for endpoints

    Expects JWT token in Authorization header:
    Authorization: Bearer <token>

    Sets g.user_id and g.user for use in endpoint
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from header
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({'status': 'error', 'message': 'Missing authorization header'}), 401

        # Extract token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'status': 'error', 'message': 'Invalid authorization header format'}), 401

        token = parts[1]

        # Verify token
        user_id = AuthService.verify_token(token, current_app.config['SECRET_KEY'])

        if not user_id:
            return jsonify({'status': 'error', 'message': 'Invalid or expired token'}), 401

        # Get user from database
        from app import db
        user = db.session.get(User, user_id)

        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 401

        # Set user context
        g.user_id = user_id
        g.user = user

        return f(*args, **kwargs)

    return decorated_function


def require_admin(f):
    """
    Decorator to require admin role

    Must be used after @require_auth
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user') or not g.user.is_admin:
            return jsonify({'status': 'error', 'message': 'Admin access required'}), 403

        return f(*args, **kwargs)

    return decorated_function
