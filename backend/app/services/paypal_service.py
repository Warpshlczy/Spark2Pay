"""
PayPal Execution Layer for Spark2Pay
=====================================

The "last mile" that turns AI savings advice into real action.

Two interchangeable backends behind one interface:

- sandbox:    real PayPal REST APIs (api-m.sandbox.paypal.com) using OAuth 2.0
              client credentials. Orders v2 for one-off payments, Subscriptions
              v1 for recurring billing management.
- simulation: a deterministic local simulator with the same call signatures.
              Zero network, zero credentials - used for local development,
              CI tests, and judges running the demo without PayPal keys.

Every method returns plain dicts and never touches the database; audit
persistence lives in the API layer (app/api/v1/paypal.py).
"""
import time
import threading
import uuid

import requests
from flask import current_app


class PayPalConfigError(Exception):
    """Raised when PayPal is not properly configured for the active mode."""


class PayPalAPIError(Exception):
    """Raised when a PayPal API call fails (or the simulator rejects an action)."""

    def __init__(self, message, status_code=None, details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self):
        return {
            'message': self.message,
            'status_code': self.status_code,
            'details': self.details
        }


class TokenManager:
    """OAuth 2.0 client-credentials token cache (thread-safe)."""

    _lock = threading.Lock()
    _cached_token = None
    _expires_at = 0.0

    @classmethod
    def get_access_token(cls):
        """Return a cached access token, refreshing it when close to expiry."""
        with cls._lock:
            if cls._cached_token and time.time() < cls._expires_at - 60:
                return cls._cached_token

            client_id = current_app.config.get('PAYPAL_CLIENT_ID')
            client_secret = current_app.config.get('PAYPAL_CLIENT_SECRET')
            if not client_id or not client_secret:
                raise PayPalConfigError(
                    'PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are not configured. '
                    'Set them in .env or switch PAYPAL_MODE=simulation.'
                )

            api_base = cls._api_base()
            try:
                resp = requests.post(
                    f'{api_base}/v1/oauth2/token',
                    auth=(client_id, client_secret),
                    data={'grant_type': 'client_credentials'},
                    headers={'Accept': 'application/json'},
                    timeout=15
                )
            except requests.RequestException as exc:
                raise PayPalAPIError(f'PayPal OAuth request failed: {exc}') from exc

            if resp.status_code != 200:
                raise PayPalAPIError(
                    'PayPal OAuth token request failed',
                    status_code=resp.status_code,
                    details={'response': resp.text[:500]}
                )

            data = resp.json()
            cls._cached_token = data['access_token']
            cls._expires_at = time.time() + int(data.get('expires_in', 3600))
            return cls._cached_token

    @classmethod
    def invalidate(cls):
        with cls._lock:
            cls._cached_token = None
            cls._expires_at = 0.0

    @staticmethod
    def _api_base():
        mode = current_app.config.get('PAYPAL_MODE')
        return (current_app.config['PAYPAL_SANDBOX_BASE'] if mode == 'sandbox'
                else current_app.config['PAYPAL_LIVE_BASE'])

    @classmethod
    def reset_for_tests(cls):
        cls.invalidate()


class PayPalService:
    """Unified execution interface over PayPal Orders v2 + Subscriptions v1."""

    # ------------------------------------------------------------------ #
    # Mode helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def is_simulation():
        return current_app.config.get('PAYPAL_MODE') == 'simulation'

    @staticmethod
    def mode():
        return current_app.config.get('PAYPAL_MODE', 'simulation')

    @classmethod
    def _api_base(cls):
        if cls.is_simulation():
            return 'simulator://paypal'
        return TokenManager._api_base()

    @classmethod
    def _headers(cls):
        return {
            'Authorization': f'Bearer {TokenManager.get_access_token()}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    @staticmethod
    def _sim_id(prefix):
        return f'SIM-{prefix}-{uuid.uuid4().hex[:12].upper()}'

    @classmethod
    def _request(cls, method, path, json_body=None):
        """Single HTTP entry point (sandbox mode only) with error wrapping."""
        url = f'{cls._api_base()}{path}'
        try:
            resp = requests.request(
                method, url, json=json_body, headers=cls._headers(), timeout=20
            )
        except requests.RequestException as exc:
            raise PayPalAPIError(f'PayPal request failed: {exc}') from exc

        if resp.status_code >= 400:
            details = {}
            try:
                details = resp.json()
            except ValueError:
                details = {'raw': resp.text[:500]}
            raise PayPalAPIError(
                f'PayPal API error on {method} {path}',
                status_code=resp.status_code,
                details=details
            )
        return resp

    # ------------------------------------------------------------------ #
    # Orders v2 - one-off payments (e.g. pay an annual plan now)
    # ------------------------------------------------------------------ #

    @classmethod
    def create_order(cls, amount, currency, description, action_id,
                     subscription_id=None):
        """
        Create a CAPTURE order and return {order_id, approve_link, status}.

        `action_id` is the Spark2Pay audit row id; it rides along as
        reference_id so webhook events can be correlated back to the audit
        trail.
        """
        frontend = current_app.config.get('FRONTEND_URL', 'http://localhost:5173')
        return_url = f'{frontend}/paypal/return?action_id={action_id}'
        cancel_url = f'{frontend}/paypal/cancel?action_id={action_id}'

        if cls.is_simulation():
            return {
                'order_id': cls._sim_id('ORD'),
                'approve_link': f'{frontend}/paypal/simulator/{action_id}',
                'status': 'CREATED',
                'mode': 'simulation'
            }

        payload = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'reference_id': str(action_id),
                'custom_id': str(subscription_id) if subscription_id else None,
                'description': (description or 'Spark2Pay subscription payment')[:127],
                'amount': {'currency_code': currency, 'value': f'{amount:.2f}'}
            }],
            'payment_source': {
                'paypal': {
                    'experience_context': {
                        'brand_name': 'Spark2Pay',
                        'user_action': 'PAY_NOW',
                        'return_url': return_url,
                        'cancel_url': cancel_url
                    }
                }
            }
        }
        # Drop None keys (custom_id may be None)
        payload['purchase_units'][0] = {
            k: v for k, v in payload['purchase_units'][0].items() if v is not None
        }

        resp = cls._request('POST', '/v2/checkout/orders', payload)
        data = resp.json()
        approve_link = next(
            (link['href'] for link in data.get('links', [])
             if link.get('rel') == 'approve'),
            return_url
        )
        return {
            'order_id': data['id'],
            'approve_link': approve_link,
            'status': data.get('status', 'CREATED'),
            'mode': 'sandbox'
        }

    @classmethod
    def capture_order(cls, order_id):
        """
        Capture an approved order. Idempotent: capturing an already-captured
        order surfaces PayPal's ORDER_ALREADY_CAPTURED as a success.
        """
        if cls.is_simulation():
            return {
                'status': 'COMPLETED',
                'capture_id': cls._sim_id('CAP'),
                'mode': 'simulation'
            }

        try:
            resp = cls._request('POST', f'/v2/checkout/orders/{order_id}/capture')
            data = resp.json()
            capture = (data.get('purchase_units', [{}])[0]
                       .get('payments', {}).get('captures', [{}])[0])
            return {
                'status': data.get('status', 'COMPLETED'),
                'capture_id': capture.get('id'),
                'mode': 'sandbox'
            }
        except PayPalAPIError as exc:
            details = str(exc.details)
            if exc.status_code in (400, 422) and 'ORDER_ALREADY_CAPTURED' in details:
                return {'status': 'COMPLETED', 'capture_id': None,
                        'mode': 'sandbox', 'idempotent': True}
            raise

    # ------------------------------------------------------------------ #
    # Subscriptions v1 - recurring billing management
    # ------------------------------------------------------------------ #

    @classmethod
    def cancel_subscription(cls, paypal_subscription_id, reason):
        """Cancel a PayPal-managed subscription. Idempotent on re-cancel."""
        if cls.is_simulation():
            return {'status': 'CANCELLED', 'mode': 'simulation'}

        try:
            resp = cls._request(
                'POST',
                f'/v1/billing/subscriptions/{paypal_subscription_id}/cancel',
                {'reason': (reason or 'Cancelled via Spark2Pay')[:127]}
            )
            return {'status': 'CANCELLED' if resp.status_code == 204
                    else 'ACCEPTED', 'mode': 'sandbox'}
        except PayPalAPIError as exc:
            if exc.status_code == 422:
                # Already cancelled / already suspended - treat as done
                return {'status': 'CANCELLED', 'mode': 'sandbox',
                        'idempotent': True}
            raise

    @classmethod
    def suspend_subscription(cls, paypal_subscription_id, reason):
        if cls.is_simulation():
            return {'status': 'SUSPENDED', 'mode': 'simulation'}

        try:
            cls._request(
                'POST',
                f'/v1/billing/subscriptions/{paypal_subscription_id}/suspend',
                {'reason': (reason or 'Suspended via Spark2Pay')[:127]}
            )
            return {'status': 'SUSPENDED', 'mode': 'sandbox'}
        except PayPalAPIError as exc:
            if exc.status_code == 422:
                return {'status': 'SUSPENDED', 'mode': 'sandbox',
                        'idempotent': True}
            raise

    @classmethod
    def activate_subscription(cls, paypal_subscription_id, reason):
        if cls.is_simulation():
            return {'status': 'ACTIVE', 'mode': 'simulation'}

        try:
            cls._request(
                'POST',
                f'/v1/billing/subscriptions/{paypal_subscription_id}/activate',
                {'reason': (reason or 'Reactivated via Spark2Pay')[:127]}
            )
            return {'status': 'ACTIVE', 'mode': 'sandbox'}
        except PayPalAPIError as exc:
            if exc.status_code == 422:
                return {'status': 'ACTIVE', 'mode': 'sandbox',
                        'idempotent': True}
            raise

    @classmethod
    def get_subscription_details(cls, paypal_subscription_id):
        if cls.is_simulation():
            return {
                'id': paypal_subscription_id,
                'status': 'ACTIVE',
                'mode': 'simulation'
            }
        resp = cls._request('GET', f'/v1/billing/subscriptions/{paypal_subscription_id}')
        data = resp.json()
        data['mode'] = 'sandbox'
        return data

    # ------------------------------------------------------------------ #
    # Webhooks
    # ------------------------------------------------------------------ #

    @classmethod
    def verify_webhook(cls, headers, raw_body):
        """
        Verify a webhook transmission against PayPal's verify-webhook-signature
        API. In simulation mode (no webhook id configured) events are accepted
        but tagged, since the simulator never sends real webhooks - local
        tooling may post synthetic events instead.
        """
        if cls.is_simulation():
            return True, {'verified': False, 'mode': 'simulation',
                          'note': 'simulation mode: webhook accepted without '
                                  'cryptographic verification (dev only)'}

        webhook_id = current_app.config.get('PAYPAL_WEBHOOK_ID')
        if not webhook_id:
            raise PayPalConfigError('PAYPAL_WEBHOOK_ID is not configured.')

        payload = {
            'auth_algo': headers.get('PAYPAL-AUTH-ALGO'),
            'cert_url': headers.get('PAYPAL-CERT-URL'),
            'transmission_id': headers.get('PAYPAL-TRANSMISSION-ID'),
            'transmission_sig': headers.get('PAYPAL-TRANSMISSION-SIG'),
            'transmission_time': headers.get('PAYPAL-TRANSMISSION-TIME'),
            'webhook_id': webhook_id,
            'webhook_event': raw_body if isinstance(raw_body, dict) else None
        }
        if payload['webhook_event'] is None:
            return False, {'verified': False, 'reason': 'body must be JSON'}

        resp = cls._request('POST', '/v1/notifications/verify-webhook-signature', payload)
        verification = resp.json()
        verified = verification.get('verification_status') == 'SUCCESS'
        return verified, {'verified': verified, 'mode': 'sandbox'}
