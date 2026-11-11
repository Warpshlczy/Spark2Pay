"""
Subscription API Endpoints
"""
from flask import Blueprint, request, jsonify, g
from datetime import datetime
from app import db
from app.models.subscription import Subscription
from app.services.billing_cycle import BillingCycleCalculator
from app.utils.decorators import require_auth

subscriptions_bp = Blueprint('subscriptions', __name__)


@subscriptions_bp.route('', methods=['GET'])
@require_auth
def list_subscriptions():
    """
    List all subscriptions for current user

    Query parameters:
    - inactive: Include inactive subscriptions (true/false)
    - category_id: Filter by category
    - payment_method_id: Filter by payment method
    - payer_id: Filter by household member
    - sort: Sort field (name, price, next_payment)
    - order: Sort order (asc, desc)
    """
    # Get query parameters
    include_inactive = request.args.get('inactive', 'false').lower() == 'true'
    category_id = request.args.get('category_id', type=int)
    payment_method_id = request.args.get('payment_method_id', type=int)
    payer_id = request.args.get('payer_id', type=int)
    sort = request.args.get('sort', 'name')
    order = request.args.get('order', 'asc')

    # Build query
    query = db.session.query(Subscription).filter_by(user_id=g.user_id)

    # Filter by status
    if not include_inactive:
        query = query.filter_by(inactive=False)

    # Filter by category
    if category_id:
        query = query.filter_by(category_id=category_id)

    # Filter by payment method
    if payment_method_id:
        query = query.filter_by(payment_method_id=payment_method_id)

    # Filter by payer
    if payer_id:
        query = query.filter_by(payer_user_id=payer_id)

    # Sort
    if hasattr(Subscription, sort):
        sort_column = getattr(Subscription, sort)
        if order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

    subscriptions = query.all()

    return jsonify({
        'status': 'success',
        'data': [sub.to_dict() for sub in subscriptions],
        'total': len(subscriptions)
    }), 200


@subscriptions_bp.route('/<int:subscription_id>', methods=['GET'])
@require_auth
def get_subscription(subscription_id):
    """Get subscription by ID"""
    subscription = db.session.query(Subscription).filter_by(
        id=subscription_id,
        user_id=g.user_id
    ).first()

    if not subscription:
        return jsonify({'status': 'error', 'message': 'Subscription not found'}), 404

    return jsonify({
        'status': 'success',
        'data': subscription.to_dict()
    }), 200


@subscriptions_bp.route('', methods=['POST'])
@require_auth
def create_subscription():
    """
    Create new subscription

    Request body:
    {
        "name": "Netflix",
        "price": 15.99,
        "currency_id": 1,
        "cycle": 3,  // 1=days, 2=weeks, 3=months, 4=years
        "frequency": 1,
        "next_payment": "2025-11-01" (optional, auto-calculated if not provided),
        "auto_renew": true,
        "url": "https://netflix.com",
        "notes": "Premium plan",
        "category_id": 1,
        "payment_method_id": 2,
        "payer_user_id": null,
        "notify_days_before": 7
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Validate required fields
    required = ['name', 'price', 'currency_id', 'cycle', 'frequency']
    for field in required:
        if field not in data:
            return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400

    # Validate cycle
    if data['cycle'] not in [1, 2, 3, 4]:
        return jsonify({'status': 'error', 'message': 'Invalid cycle. Must be 1 (days), 2 (weeks), 3 (months), or 4 (years)'}), 400

    # Validate frequency
    if data['frequency'] < 1 or data['frequency'] > 366:
        return jsonify({'status': 'error', 'message': 'Frequency must be between 1 and 366'}), 400

    # Calculate next payment if not provided
    if 'next_payment' not in data or not data['next_payment']:
        start_date = datetime.now()
        next_payment = BillingCycleCalculator.calculate_next_payment(
            start_date,
            data['cycle'],
            data['frequency']
        )
        data['next_payment'] = next_payment.date()
    else:
        # Parse date string
        try:
            data['next_payment'] = datetime.strptime(data['next_payment'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

    # Create subscription
    subscription = Subscription(
        user_id=g.user_id,
        name=data['name'],
        price=data['price'],
        currency_id=data['currency_id'],
        cycle=data['cycle'],
        frequency=data['frequency'],
        next_payment=data['next_payment'],
        auto_renew=data.get('auto_renew', True),
        logo=data.get('logo'),
        url=data.get('url'),
        notes=data.get('notes'),
        category_id=data.get('category_id'),
        payer_user_id=data.get('payer_user_id'),
        payment_method_id=data.get('payment_method_id'),
        notify_days_before=data.get('notify_days_before', 7)
    )

    db.session.add(subscription)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'data': subscription.to_dict(),
        'message': 'Subscription created successfully'
    }), 201


@subscriptions_bp.route('/<int:subscription_id>', methods=['PUT'])
@require_auth
def update_subscription(subscription_id):
    """Update subscription"""
    subscription = db.session.query(Subscription).filter_by(
        id=subscription_id,
        user_id=g.user_id
    ).first()

    if not subscription:
        return jsonify({'status': 'error', 'message': 'Subscription not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Update allowed fields
    allowed_fields = [
        'name', 'price', 'currency_id', 'cycle', 'frequency', 'next_payment',
        'auto_renew', 'logo', 'url', 'notes', 'category_id', 'payer_user_id',
        'payment_method_id', 'notify_days_before'
    ]

    for field in allowed_fields:
        if field in data:
            if field == 'next_payment' and isinstance(data[field], str):
                # Parse date
                try:
                    data[field] = datetime.strptime(data[field], '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'status': 'error', 'message': 'Invalid date format'}), 400

            setattr(subscription, field, data[field])

    db.session.commit()

    return jsonify({
        'status': 'success',
        'data': subscription.to_dict(),
        'message': 'Subscription updated successfully'
    }), 200


@subscriptions_bp.route('/<int:subscription_id>', methods=['DELETE'])
@require_auth
def delete_subscription(subscription_id):
    """Delete subscription"""
    subscription = db.session.query(Subscription).filter_by(
        id=subscription_id,
        user_id=g.user_id
    ).first()

    if not subscription:
        return jsonify({'status': 'error', 'message': 'Subscription not found'}), 404

    db.session.delete(subscription)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Subscription deleted successfully'
    }), 200


@subscriptions_bp.route('/<int:subscription_id>/mark-inactive', methods=['POST'])
@require_auth
def mark_inactive(subscription_id):
    """
    Mark subscription as inactive

    Request body:
    {
        "cancellation_date": "2025-10-20",
        "replacement_subscription_id": 5 (optional)
    }
    """
    subscription = db.session.query(Subscription).filter_by(
        id=subscription_id,
        user_id=g.user_id
    ).first()

    if not subscription:
        return jsonify({'status': 'error', 'message': 'Subscription not found'}), 404

    data = request.get_json() or {}

    # Parse cancellation date
    cancellation_date = data.get('cancellation_date')
    if cancellation_date:
        try:
            cancellation_date = datetime.strptime(cancellation_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid date format'}), 400
    else:
        cancellation_date = datetime.now().date()

    subscription.inactive = True
    subscription.cancellation_date = cancellation_date
    subscription.replacement_subscription_id = data.get('replacement_subscription_id')

    db.session.commit()

    return jsonify({
        'status': 'success',
        'data': subscription.to_dict(),
        'message': 'Subscription marked as inactive'
    }), 200


@subscriptions_bp.route('/<int:subscription_id>/renew', methods=['POST'])
@require_auth
def renew_subscription(subscription_id):
    """
    Manual renewal - updates next payment date

    For subscriptions with auto_renew=false
    """
    subscription = db.session.query(Subscription).filter_by(
        id=subscription_id,
        user_id=g.user_id
    ).first()

    if not subscription:
        return jsonify({'status': 'error', 'message': 'Subscription not found'}), 404

    # Calculate new next payment date
    current_payment = subscription.next_payment or datetime.now().date()
    new_next_payment = BillingCycleCalculator.calculate_next_payment(
        datetime.combine(current_payment, datetime.min.time()),
        subscription.cycle,
        subscription.frequency
    )

    subscription.next_payment = new_next_payment.date()
    db.session.commit()

    return jsonify({
        'status': 'success',
        'data': subscription.to_dict(),
        'message': 'Subscription renewed successfully'
    }), 200
