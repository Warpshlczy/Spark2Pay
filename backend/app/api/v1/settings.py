"""
Settings API Endpoints
Runtime-editable configuration (AI provider, API keys, execution mode).
Secrets are stored locally in the instance database and never returned
unmasked by the API.
"""
from flask import Blueprint, request, jsonify

from app import db
from app.services.runtime_config import (
    apply_setting, clear_setting, status_payload, SETTING_KEYS
)
from app.utils.decorators import require_auth

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('', methods=['GET'])
@require_auth
def get_settings():
    """Current configuration status (secrets masked)."""
    return jsonify({'status': 'success', 'data': status_payload()}), 200


@settings_bp.route('', methods=['POST'])
@require_auth
def update_settings():
    """
    Apply one or more configuration overrides.

    Request body (any subset of editable keys):
    {
        "AI_PROVIDER": "openai",
        "AI_MODEL": "gpt-4o-mini",
        "OPENAI_API_KEY": "sk-...",
        "PAYPAL_MODE": "sandbox",
        "PAYPAL_CLIENT_ID": "...",
        "PAYPAL_CLIENT_SECRET": "...",
        "PAYPAL_WEBHOOK_ID": "..."
    }

    Setting a key to "" clears the override and restores the .env default.
    """
    data = request.get_json() or {}
    if not isinstance(data, dict) or not data:
        return jsonify({'status': 'error',
                        'message': 'A JSON object of settings is required'}), 400

    unknown = [k for k in data if k not in SETTING_KEYS]
    if unknown:
        return jsonify({'status': 'error',
                        'message': f'Unknown or non-editable keys: {unknown}'}), 400

    applied, errors = [], []
    for key, value in data.items():
        ok, message = apply_setting(key, value)
        if ok:
            applied.append(key)
        else:
            errors.append({'key': key, 'message': message})

    db.session.commit()
    if errors:
        return jsonify({'status': 'error', 'applied': applied,
                        'errors': errors,
                        'data': status_payload()}), 400
    return jsonify({'status': 'success', 'applied': applied,
                    'message': f'Updated: {", ".join(applied)}',
                    'data': status_payload()}), 200


@settings_bp.route('/<key>', methods=['DELETE'])
@require_auth
def delete_setting(key):
    """Clear one override, restoring the .env-derived default."""
    ok, message = clear_setting(key)
    db.session.commit()
    if not ok:
        return jsonify({'status': 'error', 'message': message}), 400
    return jsonify({'status': 'success', 'message': message,
                    'data': status_payload()}), 200
