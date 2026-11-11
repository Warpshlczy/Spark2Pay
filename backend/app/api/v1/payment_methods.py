"""
Payment Method API Endpoints
"""
from flask import Blueprint, request, jsonify, g
from app import db
from app.models.payment_method import PaymentMethod
from app.utils.decorators import require_auth

payment_methods_bp = Blueprint('payment_methods', __name__)


@payment_methods_bp.route('', methods=['GET'])
@require_auth
def list_payment_methods():
    """
    List all payment methods for current user

    Query parameters:
    - sort: Sort field (name, order)
    - order: Sort order (asc, desc)
    """
    sort = request.args.get('sort', 'order')
    order = request.args.get('order', 'asc')

    query = db.session.query(PaymentMethod).filter_by(user_id=g.user_id)

    # Sort
    if hasattr(PaymentMethod, sort):
        sort_column = getattr(PaymentMethod, sort)
        if order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

    payment_methods = query.all()

    return jsonify({
        'status': 'success',
        'data': [pm.to_dict() for pm in payment_methods],
        'total': len(payment_methods)
    }), 200


@payment_methods_bp.route('/<int:payment_method_id>', methods=['GET'])
@require_auth
def get_payment_method(payment_method_id):
    """Get payment method by ID"""
    payment_method = db.session.query(PaymentMethod).filter_by(
        id=payment_method_id,
        user_id=g.user_id
    ).first()

    if not payment_method:
        return jsonify({'status': 'error', 'message': 'Payment method not found'}), 404

    return jsonify({
        'status': 'success',
        'data': payment_method.to_dict()
    }), 200


@payment_methods_bp.route('', methods=['POST'])
@require_auth
def create_payment_method():
    """
    Create new payment method

    Request body:
    {
        "name": "Visa ****1234",
        "order": 1
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Validate required fields
    if 'name' not in data:
        return jsonify({'status': 'error', 'message': 'name is required'}), 400

    # Check if payment method name already exists for this user
    existing = db.session.query(PaymentMethod).filter_by(
        user_id=g.user_id,
        name=data['name']
    ).first()

    if existing:
        return jsonify({'status': 'error', 'message': 'Payment method name already exists'}), 400

    # Get next order if not provided
    order = data.get('order')
    if order is None:
        max_order = db.session.query(db.func.max(PaymentMethod.order)).filter_by(
            user_id=g.user_id
        ).scalar()
        order = (max_order or 0) + 1

    # Create payment method
    payment_method = PaymentMethod(
        user_id=g.user_id,
        name=data['name'],
        order=order
    )

    db.session.add(payment_method)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'data': payment_method.to_dict(),
        'message': 'Payment method created successfully'
    }), 201


@payment_methods_bp.route('/<int:payment_method_id>', methods=['PUT'])
@require_auth
def update_payment_method(payment_method_id):
    """
    Update payment method

    Request body:
    {
        "name": "Mastercard ****5678",
        "order": 2
    }
    """
    payment_method = db.session.query(PaymentMethod).filter_by(
        id=payment_method_id,
        user_id=g.user_id
    ).first()

    if not payment_method:
        return jsonify({'status': 'error', 'message': 'Payment method not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Check for duplicate name
    if 'name' in data and data['name'] != payment_method.name:
        existing = db.session.query(PaymentMethod).filter_by(
            user_id=g.user_id,
            name=data['name']
        ).first()
        if existing:
            return jsonify({'status': 'error', 'message': 'Payment method name already exists'}), 400

    # Update allowed fields
    if 'name' in data:
        payment_method.name = data['name']
    if 'order' in data:
        payment_method.order = data['order']

    db.session.commit()

    return jsonify({
        'status': 'success',
        'data': payment_method.to_dict(),
        'message': 'Payment method updated successfully'
    }), 200


@payment_methods_bp.route('/<int:payment_method_id>', methods=['DELETE'])
@require_auth
def delete_payment_method(payment_method_id):
    """Delete payment method"""
    payment_method = db.session.query(PaymentMethod).filter_by(
        id=payment_method_id,
        user_id=g.user_id
    ).first()

    if not payment_method:
        return jsonify({'status': 'error', 'message': 'Payment method not found'}), 404

    # Check if payment method is being used by subscriptions
    from app.models.subscription import Subscription
    subscriptions_count = db.session.query(Subscription).filter_by(
        payment_method_id=payment_method_id
    ).count()

    if subscriptions_count > 0:
        return jsonify({
            'status': 'error',
            'message': f'Cannot delete payment method. {subscriptions_count} subscription(s) are using it.'
        }), 400

    db.session.delete(payment_method)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Payment method deleted successfully'
    }), 200
