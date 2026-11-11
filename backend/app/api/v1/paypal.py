"""
PayPal Execution API Endpoints
==============================

The execution half of Spark2Pay's agentic loop:

    AI advice card -> user clicks "Manage with PayPal"
        POST /actions            -> begin action, get approve link + audit id
        (user approves in PayPal / confirm page)
        POST /actions/<id>/complete -> execute capture/cancel, write audit
        GET  /actions            -> audit trail
        POST /webhook            -> async PayPal events (defense-in-depth closure)
"""
from datetime import datetime

from flask import Blueprint, request, jsonify, g, current_app

from app import db
from app.models.subscription import Subscription
from app.models.paypal_action import PayPalAction
from app.services.billing_cycle import BillingCycleCalculator
from app.services.notifications.notification_manager import NotificationManager
from app.services.paypal_service import (
    PayPalService,
    PayPalAPIError,
    PayPalConfigError
)
from app.utils.decorators import require_auth

paypal_bp = Blueprint('paypal', __name__)


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #

def _load_subscription(subscription_id):
    return db.session.query(Subscription).filter_by(
        id=subscription_id, user_id=g.user_id
    ).first()


def _load_action(action_id):
    return db.session.query(PayPalAction).filter_by(
        id=action_id, user_id=g.user_id
    ).first()


def _monthly_cost(subscription):
    return round(BillingCycleCalculator.calculate_monthly_cost(
        subscription.price, subscription.cycle, subscription.frequency
    ), 2)


def _notify(user_id, title, message, subscription_data=None):
    """Best-effort fan-out to the user's configured notification channels."""
    try:
        NotificationManager.send_notification(user_id, title, message, subscription_data)
    except Exception as exc:  # notifications must never break execution
        current_app.logger.warning('Notification dispatch failed: %s', exc)


# ---------------------------------------------------------------------- #
# Configuration status (for the Settings page)
# ---------------------------------------------------------------------- #

@paypal_bp.route('/config', methods=['GET'])
@require_auth
def paypal_config():
    """Expose execution-layer status (never secrets)."""
    cfg = current_app.config
    return jsonify({
        'status': 'success',
        'data': {
            'mode': cfg.get('PAYPAL_MODE'),
            'sandbox_configured': bool(cfg.get('PAYPAL_CLIENT_ID') and
                                       cfg.get('PAYPAL_CLIENT_SECRET')),
            'webhook_configured': bool(cfg.get('PAYPAL_WEBHOOK_ID')),
            'capabilities': [
                {'action': 'cancel', 'requires_approval': True},
                {'action': 'suspend', 'requires_approval': True},
                {'action': 'activate', 'requires_approval': True},
                {'action': 'pay', 'requires_approval': True}
            ]
        }
    }), 200


# ---------------------------------------------------------------------- #
# Begin an action
# ---------------------------------------------------------------------- #

@paypal_bp.route('/actions', methods=['POST'])
@require_auth
def begin_action():
    """
    Begin a PayPal-backed execution for a subscription.

    Request body:
    {
        "subscription_id": 3,            (required)
        "action_type": "cancel",         (required: cancel|suspend|activate|pay)
        "reason": "Unused for 90 days",  (optional)
        "amount": 14.99,                 (pay only; defaults to monthly cost)
        "currency": "USD"                (pay only; defaults to subscription currency)
    }

    Response:
    {
        "status": "success",
        "data": {
            "action_id": 12,
            "status": "pending_approval",
            "approve_link": "https://www.sandbox.paypal.com/checkoutnow?token=...",
            "mode": "sandbox"
        }
    }
    """
    data = request.get_json() or {}
    subscription_id = data.get('subscription_id')
    action_type = data.get('action_type')

    if not subscription_id or not action_type:
        return jsonify({'status': 'error',
                        'message': 'subscription_id and action_type are required'}), 400

    if action_type not in PayPalAction.ALLOWED_ACTIONS:
        return jsonify({'status': 'error',
                        'message': f'action_type must be one of '
                                   f'{list(PayPalAction.ALLOWED_ACTIONS)}'}), 400

    subscription = _load_subscription(subscription_id)
    if not subscription:
        return jsonify({'status': 'error', 'message': 'Subscription not found'}), 404
    if subscription.inactive:
        return jsonify({'status': 'error',
                        'message': 'Subscription is already inactive'}), 409

    # Manage-subscription actions require a PayPal billing linkage
    if action_type in (PayPalAction.ACTION_CANCEL,
                       PayPalAction.ACTION_SUSPEND,
                       PayPalAction.ACTION_ACTIVATE):
        if not subscription.paypal_subscription_id:
            return jsonify({
                'status': 'error',
                'message': 'This subscription is not billed through PayPal '
                           'Subscriptions and cannot be managed here. Cancel '
                           'it manually on the merchant site or link its PayPal '
                           'subscription id.',
                'code': 'not_paypal_managed'
            }), 409

    # Money fields (pay)
    amount = data.get('amount')
    currency = data.get('currency')
    monthly = _monthly_cost(subscription)
    if action_type == PayPalAction.ACTION_PAY:
        if amount is None:
            amount = round(subscription.price, 2)
        if currency is None:
            currency = subscription.currency.code if subscription.currency else 'USD'
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return jsonify({'status': 'error', 'message': 'amount must be numeric'}), 400
        if amount <= 0:
            return jsonify({'status': 'error', 'message': 'amount must be positive'}), 400

    savings = monthly if action_type == PayPalAction.ACTION_CANCEL else None

    # 1. Create the audit row first - it ids the PayPal calls
    action = PayPalAction(
        user_id=g.user_id,
        subscription_id=subscription.id,
        action_type=action_type,
        status=PayPalAction.STATUS_PENDING_APPROVAL,
        reason=data.get('reason'),
        amount=amount,
        currency=currency,
        estimated_monthly_savings=savings,
        paypal_subscription_id=subscription.paypal_subscription_id,
        paypal_mode=PayPalService.mode()
    )
    action.set_payload({
        'subscription_name': subscription.name,
        'monthly_cost': monthly,
        'origin': data.get('origin', 'manual')
    })
    db.session.add(action)
    db.session.commit()

    # 2. Create the PayPal artifact that needs user approval
    try:
        if action_type == PayPalAction.ACTION_PAY:
            result = PayPalService.create_order(
                amount=amount,
                currency=currency,
                description=f'{subscription.name} - subscription payment',
                action_id=action.id,
                subscription_id=subscription.id
            )
            action.paypal_order_id = result['order_id']
            approve_link = result['approve_link']
        else:
            # PayPal subscription cancel/suspend/activate has no hosted approval
            # screen, so Spark2Pay provides the confirmation step locally - the
            # two-step pattern (approve -> execute) stays consistent.
            approve_link = (f"{current_app.config.get('FRONTEND_URL', 'http://localhost:5173')}"
                            f"/paypal/approve/{action.id}")
    except (PayPalAPIError, PayPalConfigError) as exc:
        action.status = PayPalAction.STATUS_FAILED
        action.error = str(exc)
        db.session.commit()
        status_code = 503 if isinstance(exc, PayPalConfigError) else 502
        return jsonify({'status': 'error', 'message': str(exc),
                        'action_id': action.id}), status_code

    db.session.commit()
    return jsonify({
        'status': 'success',
        'data': {
            'action_id': action.id,
            'status': action.status,
            'action_type': action_type,
            'approve_link': approve_link,
            'estimated_monthly_savings': savings,
            'mode': action.paypal_mode
        }
    }), 201


# ---------------------------------------------------------------------- #
# Complete an action (after user approval)
# ---------------------------------------------------------------------- #

@paypal_bp.route('/actions/<int:action_id>/complete', methods=['POST'])
@require_auth
def complete_action(action_id):
    """
    Execute the approved action and close the loop:
    - pay      -> capture the order
    - cancel   -> cancel PayPal subscription + mark tracking row inactive
    - suspend  -> suspend PayPal subscription
    - activate -> reactivate PayPal subscription
    """
    action = _load_action(action_id)
    if not action:
        return jsonify({'status': 'error', 'message': 'Action not found'}), 404

    if action.status != PayPalAction.STATUS_PENDING_APPROVAL:
        return jsonify({'status': 'error',
                        'message': f'Action is {action.status}, not pending_approval',
                        'data': action.to_dict()}), 409

    subscription = db.session.get(Subscription, action.subscription_id) \
        if action.subscription_id else None

    action.status = PayPalAction.STATUS_EXECUTING
    db.session.commit()

    try:
        if action.action_type == PayPalAction.ACTION_PAY:
            result = PayPalService.capture_order(action.paypal_order_id)
            action.paypal_capture_id = result.get('capture_id')

        elif action.action_type == PayPalAction.ACTION_CANCEL:
            result = PayPalService.cancel_subscription(
                action.paypal_subscription_id,
                action.reason or 'Cancelled via Spark2Pay'
            )
            # Closed loop: the execution writes back into Spark2Pay tracking
            if subscription:
                subscription.inactive = True
                subscription.cancellation_date = datetime.now().date()
                subscription.auto_renew = False

        elif action.action_type == PayPalAction.ACTION_SUSPEND:
            result = PayPalService.suspend_subscription(
                action.paypal_subscription_id,
                action.reason or 'Suspended via Spark2Pay'
            )

        elif action.action_type == PayPalAction.ACTION_ACTIVATE:
            result = PayPalService.activate_subscription(
                action.paypal_subscription_id,
                action.reason or 'Reactivated via Spark2Pay'
            )

    except (PayPalAPIError, PayPalConfigError) as exc:
        action.status = PayPalAction.STATUS_FAILED
        action.error = str(exc)
        db.session.commit()
        return jsonify({'status': 'error', 'message': str(exc),
                        'data': action.to_dict()}), 502

    action.status = PayPalAction.STATUS_COMPLETED
    action.executed_at = datetime.now()
    payload = action.get_payload()
    payload['paypal_result'] = result
    action.set_payload(payload)
    db.session.commit()

    savings = action.estimated_monthly_savings
    sub_data = subscription.to_dict() if subscription else None
    if action.action_type == PayPalAction.ACTION_CANCEL and savings:
        _notify(
            g.user_id,
            'Subscription cancelled via PayPal',
            f'{payload.get("subscription_name", "Subscription")} was cancelled. '
            f'Estimated savings: ${savings:.2f}/month.',
            sub_data
        )

    return jsonify({
        'status': 'success',
        'data': action.to_dict(),
        'message': (f'Cancelled via PayPal. Estimated savings: '
                    f'${savings:.2f}/month' if savings else
                    f'{action.action_type} executed via PayPal')
    }), 200


# ---------------------------------------------------------------------- #
# Reject / list audit trail
# ---------------------------------------------------------------------- #

@paypal_bp.route('/actions/<int:action_id>/reject', methods=['POST'])
@require_auth
def reject_action(action_id):
    """User dismissed the approval step - keep the audit trail honest."""
    action = _load_action(action_id)
    if not action:
        return jsonify({'status': 'error', 'message': 'Action not found'}), 404

    if action.status != PayPalAction.STATUS_PENDING_APPROVAL:
        return jsonify({'status': 'error',
                        'message': f'Action is {action.status}'}), 409

    action.status = PayPalAction.STATUS_REJECTED
    action.executed_at = datetime.now()
    db.session.commit()
    return jsonify({'status': 'success', 'data': action.to_dict()}), 200


@paypal_bp.route('/actions/<int:action_id>', methods=['GET'])
@require_auth
def get_action(action_id):
    """Single audit record (used by the approval confirmation page)."""
    action = _load_action(action_id)
    if not action:
        return jsonify({'status': 'error', 'message': 'Action not found'}), 404
    return jsonify({'status': 'success', 'data': action.to_dict()}), 200


@paypal_bp.route('/actions', methods=['GET'])
@require_auth
def list_actions():
    """
    Audit trail for the current user.

    Query params: status, action_type, subscription_id, limit (default 50)
    """
    query = db.session.query(PayPalAction).filter_by(user_id=g.user_id)

    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    action_type = request.args.get('action_type')
    if action_type:
        query = query.filter_by(action_type=action_type)
    subscription_id = request.args.get('subscription_id', type=int)
    if subscription_id:
        query = query.filter_by(subscription_id=subscription_id)

    limit = min(request.args.get('limit', 50, type=int), 200)
    actions = query.order_by(PayPalAction.created_at.desc()).limit(limit).all()

    return jsonify({
        'status': 'success',
        'data': [a.to_dict() for a in actions],
        'total': len(actions)
    }), 200


# ---------------------------------------------------------------------- #
# Webhooks - async closure for events PayPal sends on its own
# ---------------------------------------------------------------------- #

@paypal_bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Receive PayPal webhook events. Unauthenticated endpoint - requests are
    verified against PayPal's verify-webhook-signature API (sandbox mode) or
    accepted with a dev-only tag (simulation mode).

    Handled events:
    - PAYMENT.CAPTURE.COMPLETED      -> close a pending/completing pay action
    - BILLING.SUBSCRIPTION.CANCELLED -> mark the tracked subscription inactive
    """
    event = request.get_json(silent=True)
    if not event:
        return jsonify({'status': 'error', 'message': 'JSON body required'}), 400

    try:
        verified, info = PayPalService.verify_webhook(request.headers, event)
    except PayPalConfigError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 503
    except PayPalAPIError as exc:
        return jsonify({'status': 'error', 'message': exc.message}), 502

    if not verified:
        return jsonify({'status': 'error', 'message': 'Webhook verification failed'}), 401

    event_type = event.get('event_type')
    resource = event.get('resource', {}) or {}
    handled = False

    if event_type == 'PAYMENT.CAPTURE.COMPLETED':
        order_id = (resource.get('supplementary_data', {})
                    .get('related_ids', {}).get('order_id'))
        query = db.session.query(PayPalAction).filter_by(
            action_type=PayPalAction.ACTION_PAY
        )
        action = query.filter_by(paypal_order_id=order_id).first() if order_id \
            else None
        if action and action.status != PayPalAction.STATUS_COMPLETED:
            action.status = PayPalAction.STATUS_COMPLETED
            action.paypal_capture_id = resource.get('id')
            action.executed_at = datetime.now()
            db.session.commit()
            handled = True

    elif event_type == 'BILLING.SUBSCRIPTION.CANCELLED':
        paypal_sub_id = resource.get('id')
        if paypal_sub_id:
            subscription = db.session.query(Subscription).filter_by(
                paypal_subscription_id=paypal_sub_id
            ).first()
            if subscription and not subscription.inactive:
                subscription.inactive = True
                subscription.cancellation_date = datetime.now().date()
                subscription.auto_renew = False
                db.session.commit()
                _notify(
                    subscription.user_id,
                    'Subscription cancelled on PayPal',
                    f'{subscription.name} was cancelled on PayPal and marked '
                    f'inactive in Spark2Pay.',
                    subscription.to_dict()
                )
                handled = True

    return jsonify({'status': 'success', 'event_type': event_type,
                    'handled': handled, 'verification': info}), 200
