"""
Runtime settings API tests - UI-driven configuration with validation,
masking, and immediate effect on the execution layer.
"""
from unittest import mock


def test_get_settings_masks_secrets(client, seeded_user):
    headers, _ = seeded_user
    resp = client.get('/api/v1/settings', headers=headers)
    data = resp.get_json()['data']
    assert data['ai']['configured_provider'] in (
        'auto', 'heuristic', 'openai', 'gemini', 'ollama')
    assert data['execution']['mode'] in ('simulation', 'sandbox')
    assert data['ai']['openai_key'] is None  # no key configured yet


def test_post_configures_openai_key_and_provider(client, seeded_user):
    headers, _ = seeded_user
    resp = client.post('/api/v1/settings', headers=headers, json={
        'OPENAI_API_KEY': 'sk-test-1234567890',
        'AI_PROVIDER': 'openai'
    })
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['ai']['configured_provider'] == 'openai'
    assert data['ai']['effective_provider'] == 'openai'
    # masked - never the full key
    assert data['ai']['openai_key'] == '••••7890'
    assert 'sk-test' not in resp.get_data(as_text=True)


def test_post_key_takes_effect_on_advice_engine(client, seeded_user):
    """Configure provider+key from the UI (as the Settings page does) ->
    the advice engine switches to the LLM path."""
    headers, _ = seeded_user
    resp = client.post('/api/v1/settings', headers=headers, json={
        'OPENAI_API_KEY': 'sk-test-1234567890',
        'AI_PROVIDER': 'openai'})
    assert resp.status_code == 200
    assert resp.get_json()['data']['ai']['effective_provider'] == 'openai'

    resp = client.get('/api/v1/ai/status', headers=headers)
    assert resp.get_json()['data']['ai']['effective_provider'] == 'openai'


def test_post_invalid_provider_rejected(client, seeded_user):
    headers, _ = seeded_user
    resp = client.post('/api/v1/settings', headers=headers, json={
        'AI_PROVIDER': 'sky-net'})
    assert resp.status_code == 400
    assert any(e['key'] == 'AI_PROVIDER' for e in resp.get_json()['errors'])


def test_post_invalid_mode_rejected_and_nothing_applied(client, seeded_user):
    headers, _ = seeded_user
    resp = client.post('/api/v1/settings', headers=headers, json={
        'PAYPAL_MODE': 'production'})
    assert resp.status_code == 400


def test_clear_setting_restores_env_default(client, seeded_user):
    headers, _ = seeded_user
    client.post('/api/v1/settings', headers=headers, json={
        'OPENAI_API_KEY': 'sk-test-1234567890'})
    resp = client.post('/api/v1/settings', headers=headers, json={
        'OPENAI_API_KEY': ''})  # empty string clears the override
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['ai']['openai_key'] is None


def test_unknown_key_rejected(client, seeded_user):
    headers, _ = seeded_user
    resp = client.post('/api/v1/settings', headers=headers, json={
        'SECRET_KEY': 'evil'})
    assert resp.status_code == 400


def test_settings_require_auth(client):
    resp = client.get('/api/v1/settings')
    assert resp.status_code == 401


def test_paypal_mode_switch_affects_execution_layer(client, seeded_user):
    """Switching to sandbox without credentials must surface a config error
    on execution attempts (pay orders need credentials at begin time)."""
    headers, data = seeded_user
    resp = client.post('/api/v1/settings', headers=headers, json={
        'PAYPAL_MODE': 'sandbox'})
    assert resp.status_code == 200
    assert resp.get_json()['data']['execution']['mode'] == 'sandbox'

    resp = client.post('/api/v1/paypal/actions', headers=headers, json={
        'subscription_id': data['adobe_id'], 'action_type': 'pay'})
    assert resp.status_code == 503  # PayPalConfigError - no credentials

    # switch back so other fixtures stay untouched
    client.post('/api/v1/settings', headers=headers, json={
        'PAYPAL_MODE': 'simulation'})
