"""
Notification API Endpoints
"""
from flask import Blueprint, request, jsonify, g
from app import db
from app.models.notification import (
    NotificationSettings,
    EmailNotification,
    DiscordNotification,
    TelegramNotification,
    PushoverNotification,
    NotificationLog
)
from app.services.notifications.notification_manager import NotificationManager
from app.utils.decorators import require_auth

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/settings', methods=['GET'])
@require_auth
def get_notification_settings():
    """
    Get notification settings for current user

    Returns all notification channel configurations
    """
    settings = db.session.query(NotificationSettings).filter_by(user_id=g.user_id).first()

    if not settings:
        # Create default settings
        settings = NotificationSettings(user_id=g.user_id)
        db.session.add(settings)
        db.session.commit()

    return jsonify({
        'status': 'success',
        'data': settings.to_dict()
    }), 200


@notifications_bp.route('/settings', methods=['PUT'])
@require_auth
def update_notification_settings():
    """
    Update notification settings

    Request body:
    {
        "email_enabled": true,
        "discord_enabled": false,
        "telegram_enabled": true,
        ...
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    settings = db.session.query(NotificationSettings).filter_by(user_id=g.user_id).first()

    if not settings:
        settings = NotificationSettings(user_id=g.user_id)
        db.session.add(settings)

    # Update enabled/disabled flags
    allowed_fields = [
        'email_enabled', 'discord_enabled', 'telegram_enabled', 'pushover_enabled',
        'pushplus_enabled', 'mattermost_enabled', 'ntfy_enabled', 'gotify_enabled',
        'webhook_enabled'
    ]

    for field in allowed_fields:
        if field in data:
            setattr(settings, field, data[field])

    db.session.commit()

    return jsonify({
        'status': 'success',
        'data': settings.to_dict(),
        'message': 'Notification settings updated successfully'
    }), 200


@notifications_bp.route('/email', methods=['GET', 'POST', 'PUT'])
@require_auth
def manage_email_notification():
    """
    GET: Get email notification configuration
    POST/PUT: Create or update email notification configuration

    Request body for POST/PUT:
    {
        "smtp_address": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "user@gmail.com",
        "smtp_password": "password",
        "from_email": "user@gmail.com",
        "to_email": "user@gmail.com",
        "encryption": "tls"
    }
    """
    if request.method == 'GET':
        config = db.session.query(EmailNotification).filter_by(user_id=g.user_id).first()

        if not config:
            return jsonify({'status': 'success', 'data': None}), 200

        return jsonify({
            'status': 'success',
            'data': config.to_dict()
        }), 200

    else:  # POST or PUT
        data = request.get_json()

        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        # Validate required fields
        required = ['smtp_address', 'smtp_port', 'from_email', 'to_email']
        for field in required:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400

        config = db.session.query(EmailNotification).filter_by(user_id=g.user_id).first()

        if not config:
            config = EmailNotification(user_id=g.user_id)
            db.session.add(config)

        # Update fields
        config.smtp_address = data['smtp_address']
        config.smtp_port = data['smtp_port']
        config.smtp_username = data.get('smtp_username')
        config.smtp_password = data.get('smtp_password')
        config.from_email = data['from_email']
        config.to_email = data['to_email']
        config.encryption = data.get('encryption', 'tls')

        db.session.commit()

        return jsonify({
            'status': 'success',
            'data': config.to_dict(),
            'message': 'Email notification configured successfully'
        }), 200 if request.method == 'PUT' else 201


@notifications_bp.route('/discord', methods=['GET', 'POST', 'PUT'])
@require_auth
def manage_discord_notification():
    """
    GET: Get Discord notification configuration
    POST/PUT: Create or update Discord notification configuration

    Request body for POST/PUT:
    {
        "webhook_url": "https://discord.com/api/webhooks/..."
    }
    """
    if request.method == 'GET':
        config = db.session.query(DiscordNotification).filter_by(user_id=g.user_id).first()

        if not config:
            return jsonify({'status': 'success', 'data': None}), 200

        return jsonify({
            'status': 'success',
            'data': config.to_dict()
        }), 200

    else:  # POST or PUT
        data = request.get_json()

        if not data or 'webhook_url' not in data:
            return jsonify({'status': 'error', 'message': 'webhook_url is required'}), 400

        config = db.session.query(DiscordNotification).filter_by(user_id=g.user_id).first()

        if not config:
            config = DiscordNotification(user_id=g.user_id)
            db.session.add(config)

        config.webhook_url = data['webhook_url']
        db.session.commit()

        return jsonify({
            'status': 'success',
            'data': config.to_dict(),
            'message': 'Discord notification configured successfully'
        }), 200 if request.method == 'PUT' else 201


@notifications_bp.route('/telegram', methods=['GET', 'POST', 'PUT'])
@require_auth
def manage_telegram_notification():
    """
    GET: Get Telegram notification configuration
    POST/PUT: Create or update Telegram notification configuration

    Request body for POST/PUT:
    {
        "bot_token": "123456:ABC-DEF...",
        "chat_id": "123456789"
    }
    """
    if request.method == 'GET':
        config = db.session.query(TelegramNotification).filter_by(user_id=g.user_id).first()

        if not config:
            return jsonify({'status': 'success', 'data': None}), 200

        return jsonify({
            'status': 'success',
            'data': config.to_dict()
        }), 200

    else:  # POST or PUT
        data = request.get_json()

        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        required = ['bot_token', 'chat_id']
        for field in required:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400

        config = db.session.query(TelegramNotification).filter_by(user_id=g.user_id).first()

        if not config:
            config = TelegramNotification(user_id=g.user_id)
            db.session.add(config)

        config.bot_token = data['bot_token']
        config.chat_id = data['chat_id']
        db.session.commit()

        return jsonify({
            'status': 'success',
            'data': config.to_dict(),
            'message': 'Telegram notification configured successfully'
        }), 200 if request.method == 'PUT' else 201


@notifications_bp.route('/pushover', methods=['GET', 'POST', 'PUT'])
@require_auth
def manage_pushover_notification():
    """
    GET: Get Pushover notification configuration
    POST/PUT: Create or update Pushover notification configuration

    Request body for POST/PUT:
    {
        "user_key": "user_key_here",
        "api_token": "api_token_here",
        "priority": 0,
        "sound": "pushover"
    }
    """
    if request.method == 'GET':
        config = db.session.query(PushoverNotification).filter_by(user_id=g.user_id).first()

        if not config:
            return jsonify({'status': 'success', 'data': None}), 200

        return jsonify({
            'status': 'success',
            'data': config.to_dict()
        }), 200

    else:  # POST or PUT
        data = request.get_json()

        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        required = ['user_key', 'api_token']
        for field in required:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400

        config = db.session.query(PushoverNotification).filter_by(user_id=g.user_id).first()

        if not config:
            config = PushoverNotification(user_id=g.user_id)
            db.session.add(config)

        config.user_key = data['user_key']
        config.api_token = data['api_token']
        config.priority = data.get('priority', 0)
        config.sound = data.get('sound', 'pushover')
        db.session.commit()

        return jsonify({
            'status': 'success',
            'data': config.to_dict(),
            'message': 'Pushover notification configured successfully'
        }), 200 if request.method == 'PUT' else 201


@notifications_bp.route('/test/<channel>', methods=['POST'])
@require_auth
def test_notification(channel):
    """
    Test notification channel

    Args:
        channel: Channel name (email, discord, telegram, pushover, etc.)
    """
    success = NotificationManager.test_channel(g.user_id, channel)

    if success:
        return jsonify({
            'status': 'success',
            'message': f'{channel.capitalize()} notification test successful'
        }), 200
    else:
        return jsonify({
            'status': 'error',
            'message': f'{channel.capitalize()} notification test failed'
        }), 400


@notifications_bp.route('/send', methods=['POST'])
@require_auth
def send_notification():
    """
    Send manual notification

    Request body:
    {
        "title": "Test Notification",
        "message": "This is a test message",
        "channels": ["email", "discord"]  // Optional, defaults to all enabled
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    if 'title' not in data or 'message' not in data:
        return jsonify({'status': 'error', 'message': 'title and message are required'}), 400

    results = NotificationManager.send_notification(
        g.user_id,
        data['title'],
        data['message'],
        channels=data.get('channels')
    )

    successful = [k for k, v in results.items() if v]
    failed = [k for k, v in results.items() if not v]

    return jsonify({
        'status': 'success' if successful else 'error',
        'data': {
            'successful': successful,
            'failed': failed,
            'results': results
        }
    }), 200


@notifications_bp.route('/log', methods=['GET'])
@require_auth
def get_notification_log():
    """
    Get notification history

    Query parameters:
    - limit: Number of records to return (default: 50)
    - channel: Filter by channel name
    """
    limit = request.args.get('limit', 50, type=int)
    channel = request.args.get('channel')

    query = db.session.query(NotificationLog).filter_by(user_id=g.user_id)

    if channel:
        query = query.filter_by(channel=channel)

    logs = query.order_by(NotificationLog.created_at.desc()).limit(limit).all()

    return jsonify({
        'status': 'success',
        'data': [log.to_dict() for log in logs],
        'total': len(logs)
    }), 200
