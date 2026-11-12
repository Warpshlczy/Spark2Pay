"""
PayPal execution layer tests - simulation mode end-to-end, sandbox mode with
mocked HTTP.
"""
from unittest import mock

import pytest

from app.services.paypal_service import (
    PayPalService, PayPalAPIError, PayPalConfigError, TokenManager
)


# --------------------------------------------------------------------- #
# Simulation mode - deterministic, offline
# --------------------------------------------------------------------- #

def test_simulation_create_order(app):
    with app.app_context():
        result = PayPalService.create_order(
            amount=19.99, currency='USD',
            description='Test order', action_id=1, subscription_id=5
        )
        assert result['order_id'].startswith('SIM-ORD-')
        assert result['approve_link'].endswith('/paypal/simulator/1')
        assert result['status'] == 'CREATED'


def test_simulation_capture_and_cancel(app):
    with app.app_context():
        capture = PayPalService.capture_order('SIM-ORD-X')
        assert capture['status'] == 'COMPLETED'
        assert capture['capture_id'].startswith('SIM-CAP-')

        cancel = PayPalService.cancel_subscription('SIM-SUB-X', 'reason')
        assert cancel['status'] == 'CANCELLED'

        suspend = PayPalService.suspend_subscription('SIM-SUB-X', 'reason')
        assert suspend['status'] == 'SUSPENDED'

        activate = PayPalService.activate_subscription('SIM-SUB-X', 'reason')
        assert activate['status'] == 'ACTIVE'


def test_simulation_webhook_verification_is_accepting(app):
    with app.app_context():
        verified, info = PayPalService.verify_webhook({}, {'event_type': 'X'})
        assert verified is True
        assert info['mode'] == 'simulation'


# --------------------------------------------------------------------- #
# Sandbox mode - HTTP mocked
# --------------------------------------------------------------------- #

@pytest.fixture()
def sandbox_app(app):
    app.config['PAYPAL_MODE'] = 'sandbox'
    app.config['PAYPAL_CLIENT_ID'] = 'test-client'
    app.config['PAYPAL_CLIENT_SECRET'] = 'test-secret'
    TokenManager.reset_for_tests()
    yield app
    TokenManager.reset_for_tests()


def _mock_response(status_code=200, json_data=None, text=''):
    resp = mock.Mock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = text
    return resp


def test_sandbox_token_is_cached(sandbox_app):
    with sandbox_app.app_context():
        with mock.patch('app.services.paypal_service.requests.post') as post:
            post.return_value = _mock_response(
                200, {'access_token': 'tok123', 'expires_in': 3600})
            assert TokenManager.get_access_token() == 'tok123'
            assert TokenManager.get_access_token() == 'tok123'
            assert post.call_count == 1  # second call served from cache


def test_sandbox_token_missing_credentials(sandbox_app):
    sandbox_app.config['PAYPAL_CLIENT_ID'] = None
    with sandbox_app.app_context():
        with pytest.raises(PayPalConfigError):
            TokenManager.get_access_token()


def test_sandbox_create_order_builds_payload_and_approve_link(sandbox_app):
    with sandbox_app.app_context():
        with mock.patch.object(PayPalService, '_request') as req:
            req.return_value = _mock_response(201, {
                'id': 'ORD-123',
                'status': 'CREATED',
                'links': [
                    {'rel': 'self', 'href': 'https://api/x'},
                    {'rel': 'approve', 'href': 'https://www.sandbox.paypal.com/checkoutnow?token=X'}
                ]
            })
            result = PayPalService.create_order(
                15.0, 'USD', 'desc', action_id=7, subscription_id=3)

            assert result['order_id'] == 'ORD-123'
            assert 'checkoutnow' in result['approve_link']

            method, path, payload = req.call_args[0]
            assert method == 'POST' and path == '/v2/checkout/orders'
            unit = payload['purchase_units'][0]
            assert unit['amount'] == {'currency_code': 'USD', 'value': '15.00'}
            assert unit['reference_id'] == '7'
            ctx = payload['payment_source']['paypal']['experience_context']
            assert ctx['return_url'].endswith('action_id=7')
            assert ctx['cancel_url'].endswith('action_id=7')


def test_sandbox_capture_idempotent_on_already_captured(sandbox_app):
    with sandbox_app.app_context():
        with mock.patch.object(PayPalService, '_request') as req:
            req.side_effect = PayPalAPIError(
                'already captured', status_code=422,
                details={'name': 'ORDER_ALREADY_CAPTURED'})
            result = PayPalService.capture_order('ORD-1')
            assert result['status'] == 'COMPLETED'
            assert result.get('idempotent') is True


def test_sandbox_cancel_subscription_204(sandbox_app):
    with sandbox_app.app_context():
        with mock.patch.object(PayPalService, '_request') as req:
            req.return_value = _mock_response(204)
            result = PayPalService.cancel_subscription('SUB-1', 'too pricey')
            assert result['status'] == 'CANCELLED'
            method, path, body = req.call_args[0]
            assert path == '/v1/billing/subscriptions/SUB-1/cancel'
            assert body['reason'] == 'too pricey'


def test_sandbox_cancel_422_treated_as_done(sandbox_app):
    """PayPal returns 422 when the subscription is already cancelled."""
    with sandbox_app.app_context():
        with mock.patch.object(PayPalService, '_request') as req:
            req.side_effect = PayPalAPIError('gone', status_code=422,
                                             details={'name': 'RESOURCE_NOT_FOUND'})
            result = PayPalService.cancel_subscription('SUB-1', 'x')
            assert result['status'] == 'CANCELLED'


def test_sandbox_api_error_propagates(sandbox_app):
    with sandbox_app.app_context():
        with mock.patch.object(PayPalService, '_request') as req:
            req.side_effect = PayPalAPIError('boom', status_code=500, details={})
            with pytest.raises(PayPalAPIError):
                PayPalService.cancel_subscription('SUB-1', 'x')


def test_sandbox_webhook_verification_calls_paypal(sandbox_app):
    sandbox_app.config['PAYPAL_WEBHOOK_ID'] = 'WHID'
    with sandbox_app.app_context():
        with mock.patch.object(PayPalService, '_request') as req:
            req.return_value = _mock_response(
                200, {'verification_status': 'SUCCESS'})
            verified, info = PayPalService.verify_webhook(
                {'PAYPAL-AUTH-ALGO': 'SHA256withRSA',
                 'PAYPAL-CERT-URL': 'https://cert',
                 'PAYPAL-TRANSMISSION-ID': 't1',
                 'PAYPAL-TRANSMISSION-SIG': 'sig',
                 'PAYPAL-TRANSMISSION-TIME': 'now'},
                {'event_type': 'PAYMENT.CAPTURE.COMPLETED'})
            assert verified is True
            payload = req.call_args[0][2]
            assert payload['webhook_id'] == 'WHID'
            assert payload['webhook_event']['event_type'] == 'PAYMENT.CAPTURE.COMPLETED'
