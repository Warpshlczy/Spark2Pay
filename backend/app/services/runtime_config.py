"""
Runtime configuration service
=============================

Lets the Settings UI override selected config values (AI provider, API keys,
execution mode) at runtime:

- capture_env_defaults(): remember the .env-derived values so a cleared
  override can fall back to them.
- load_persisted_settings(): re-apply stored overrides on startup.
- apply_setting() / clear_setting(): update app.config immediately and mirror
  to the app_settings table.

Only keys in SETTING_KEYS are accepted - everything else is rejected, so the
UI can never mutate arbitrary Flask config (SECRET_KEY, DATABASE_URL, ...).
"""
from flask import current_app

from app import db
from app.models.app_setting import AppSetting

# UI-configurable config keys -> secret or not
SETTING_KEYS = {
    'AI_PROVIDER': False,
    'AI_MODEL': False,
    'OPENAI_API_KEY': True,
    'PAYPAL_MODE': False,
    'PAYPAL_CLIENT_ID': False,
    'PAYPAL_CLIENT_SECRET': True,
    'PAYPAL_WEBHOOK_ID': False,
}


def init_runtime_config(app):
    """Capture env defaults and re-apply persisted overrides. Called once
    from the app factory within an app context."""
    app.extensions['config_env_defaults'] = {
        key: app.config.get(key) for key in SETTING_KEYS
    }
    load_persisted_settings(app)


def load_persisted_settings(app):
    """Re-apply stored overrides from the database (startup path)."""
    try:
        rows = db.session.query(AppSetting).all()
    except Exception:
        # Tables may not exist yet on a brand-new database (before seeding)
        return 0
    for row in rows:
        if row.key in SETTING_KEYS and row.value is not None and row.value != '':
            app.config[row.key] = row.value
    return len(rows)


def _env_default(app, key):
    return app.extensions.get('config_env_defaults', {}).get(key)


def apply_setting(key, value):
    """Validate, persist and apply one override. Returns (ok, message)."""
    if key not in SETTING_KEYS:
        return False, f'Unknown setting: {key}'
    if value is None or not isinstance(value, str) or value.strip() == '':
        return clear_setting(key)

    value = value.strip()
    cfg = current_app.config

    if key == 'AI_PROVIDER' and value not in (
            'auto', 'heuristic', 'openai', 'gemini', 'ollama'):
        return False, ('AI_PROVIDER must be one of: auto, heuristic, '
                       'openai, gemini, ollama')
    if key == 'PAYPAL_MODE' and value not in ('simulation', 'sandbox'):
        return False, 'PAYPAL_MODE must be simulation or sandbox'
    if SETTING_KEYS[key] and len(value) < 8:
        return False, f'{key} looks too short to be valid'

    cfg[key] = value
    row = db.session.get(AppSetting, key)
    if row:
        row.value = value
    else:
        db.session.add(AppSetting(key=key, value=value))
    db.session.commit()
    return True, 'saved'


def clear_setting(key):
    """Remove an override and fall back to the .env-derived default."""
    if key not in SETTING_KEYS:
        return False, f'Unknown setting: {key}'
    current_app.config[key] = _env_default(current_app, key)
    row = db.session.get(AppSetting, key)
    if row:
        db.session.delete(row)
    db.session.commit()
    return True, 'cleared'


def mask(value):
    """Never ship a full secret to the UI - show only its tail."""
    if not value:
        return None
    return '••••' + value[-4:]


def status_payload():
    """Full settings status for the UI (secrets masked)."""
    cfg = current_app.config
    return {
        'ai': {
            'configured_provider': cfg.get('AI_PROVIDER', 'auto'),
            'effective_provider': _effective_provider(cfg),
            'model': cfg.get('AI_MODEL'),
            'openai_key': mask(cfg.get('OPENAI_API_KEY')),
        },
        'execution': {
            'mode': cfg.get('PAYPAL_MODE'),
            'client_id': cfg.get('PAYPAL_CLIENT_ID'),
            'client_secret': mask(cfg.get('PAYPAL_CLIENT_SECRET')),
            'webhook_id': cfg.get('PAYPAL_WEBHOOK_ID'),
        },
        'editable_keys': sorted(SETTING_KEYS.keys()),
    }


def _effective_provider(cfg):
    provider = cfg.get('AI_PROVIDER', 'auto')
    if provider == 'auto':
        return 'openai' if cfg.get('OPENAI_API_KEY') else 'heuristic'
    return provider
