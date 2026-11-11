"""
Authentication API Endpoints
"""
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models.user import User
from app.models.currency import Currency
from app.services.auth_service import AuthService
from app.utils.validators import validate_email, validate_password, validate_username
from app.utils.decorators import require_auth

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user

    Request body:
    {
        "username": "string",
        "email": "string",
        "password": "string",
        "firstname": "string" (optional)
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Validate required fields
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    firstname = data.get('firstname', '').strip() if data.get('firstname') else None

    if not username or not email or not password:
        return jsonify({'status': 'error', 'message': 'Username, email, and password are required'}), 400

    # Validate username
    if not validate_username(username):
        return jsonify({
            'status': 'error',
            'message': 'Invalid username. Must be 3-50 characters, alphanumeric with underscore/dash, starting with letter or number'
        }), 400

    # Validate email
    if not validate_email(email):
        return jsonify({'status': 'error', 'message': 'Invalid email format'}), 400

    # Validate password
    if not validate_password(password):
        return jsonify({
            'status': 'error',
            'message': 'Password must be at least 8 characters with uppercase, lowercase, and number'
        }), 400

    # Check if username exists
    if db.session.query(User).filter_by(username=username).first():
        return jsonify({'status': 'error', 'message': 'Username already exists'}), 409

    # Check if email exists
    if db.session.query(User).filter_by(email=email).first():
        return jsonify({'status': 'error', 'message': 'Email already registered'}), 409

    # Create user
    user = User(
        username=username,
        email=email,
        password=AuthService.hash_password(password),
        firstname=firstname
    )

    # Create default USD currency for user
    usd_currency = Currency(
        user_id=user.id,
        name='US Dollar',
        code='USD',
        symbol='$',
        rate=1.0
    )

    db.session.add(user)
    db.session.flush()  # Get user.id

    usd_currency.user_id = user.id
    user.main_currency = usd_currency.id

    db.session.add(usd_currency)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'User registered successfully',
        'user': user.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login user

    Request body:
    {
        "username": "string",
        "password": "string",
        "totp_code": "string" (optional, required if 2FA enabled)
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Username and password are required'}), 400

    # Find user
    user = db.session.query(User).filter_by(username=username).first()

    if not user or not AuthService.verify_password(password, user.password):
        return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401

    # Check 2FA if enabled
    if user.totp_enabled:
        totp_code = data.get('totp_code', '').strip()

        if not totp_code:
            return jsonify({'status': 'error', 'message': '2FA code required'}), 401

        if not AuthService.verify_totp(user.totp_secret, totp_code):
            return jsonify({'status': 'error', 'message': 'Invalid 2FA code'}), 401

    # Generate JWT token
    token = AuthService.generate_token(
        user.id,
        current_app.config['SECRET_KEY'],
        current_app.config['PERMANENT_SESSION_LIFETIME']
    )

    return jsonify({
        'status': 'success',
        'token': token,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """
    Logout user (client should delete token)
    """
    return jsonify({
        'status': 'success',
        'message': 'Logged out successfully'
    }), 200


@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current user info"""
    from flask import g

    return jsonify({
        'status': 'success',
        'user': g.user.to_dict()
    }), 200


@auth_bp.route('/setup-2fa', methods=['POST'])
@require_auth
def setup_2fa():
    """
    Set up TOTP 2FA for current user

    Returns QR code for authenticator app
    """
    from flask import g

    user = g.user

    if user.totp_enabled:
        return jsonify({'status': 'error', 'message': '2FA already enabled'}), 400

    # Generate TOTP secret
    secret = AuthService.generate_totp_secret()

    # Generate provisioning URI
    totp_uri = AuthService.get_totp_uri(secret, user.username)

    # Generate QR code
    qr_code_uri = AuthService.generate_qr_code_data_uri(totp_uri)

    # Save secret (not enabled yet)
    user.totp_secret = secret
    db.session.commit()

    return jsonify({
        'status': 'success',
        'secret': secret,
        'qr_code': qr_code_uri,
        'message': 'Scan QR code with authenticator app, then verify with /verify-2fa'
    }), 200


@auth_bp.route('/verify-2fa', methods=['POST'])
@require_auth
def verify_2fa():
    """
    Verify and enable 2FA

    Request body:
    {
        "code": "123456"
    }
    """
    from flask import g
    data = request.get_json()

    user = g.user

    if user.totp_enabled:
        return jsonify({'status': 'error', 'message': '2FA already enabled'}), 400

    if not user.totp_secret:
        return jsonify({'status': 'error', 'message': 'Please setup 2FA first'}), 400

    code = data.get('code', '').strip()

    if not code:
        return jsonify({'status': 'error', 'message': 'Code required'}), 400

    # Verify code
    if not AuthService.verify_totp(user.totp_secret, code):
        return jsonify({'status': 'error', 'message': 'Invalid code'}), 401

    # Enable 2FA
    user.totp_enabled = True
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': '2FA enabled successfully'
    }), 200


@auth_bp.route('/disable-2fa', methods=['POST'])
@require_auth
def disable_2fa():
    """
    Disable 2FA

    Request body:
    {
        "password": "string",
        "code": "123456"
    }
    """
    from flask import g
    data = request.get_json()

    user = g.user

    if not user.totp_enabled:
        return jsonify({'status': 'error', 'message': '2FA not enabled'}), 400

    password = data.get('password', '')
    code = data.get('code', '').strip()

    if not password or not code:
        return jsonify({'status': 'error', 'message': 'Password and code required'}), 400

    # Verify password
    if not AuthService.verify_password(password, user.password):
        return jsonify({'status': 'error', 'message': 'Invalid password'}), 401

    # Verify code
    if not AuthService.verify_totp(user.totp_secret, code):
        return jsonify({'status': 'error', 'message': 'Invalid code'}), 401

    # Disable 2FA
    user.totp_enabled = False
    user.totp_secret = None
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': '2FA disabled successfully'
    }), 200
