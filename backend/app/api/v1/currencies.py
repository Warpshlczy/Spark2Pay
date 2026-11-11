"""
Currency API Endpoints
"""
from flask import Blueprint, request, jsonify, g
from app import db
from app.models.currency import Currency
from app.models.user import User
from app.services.currency_converter import CurrencyConverter
from app.utils.decorators import require_auth

currencies_bp = Blueprint('currencies', __name__)


@currencies_bp.route('', methods=['GET'])
@require_auth
def list_currencies():
    """
    List all currencies for current user

    Query parameters:
    - sort: Sort field (name, code, rate)
    - order: Sort order (asc, desc)
    """
    sort = request.args.get('sort', 'name')
    order = request.args.get('order', 'asc')

    query = db.session.query(Currency).filter_by(user_id=g.user_id)

    # Sort
    if hasattr(Currency, sort):
        sort_column = getattr(Currency, sort)
        if order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

    currencies = query.all()

    return jsonify({
        'status': 'success',
        'data': [currency.to_dict() for currency in currencies],
        'total': len(currencies)
    }), 200


@currencies_bp.route('/supported', methods=['GET'])
def get_supported_currencies():
    """
    Get list of supported currencies (no auth required)

    Returns dictionary of currency code -> name
    """
    supported = CurrencyConverter.get_supported_currencies()

    return jsonify({
        'status': 'success',
        'data': supported
    }), 200


@currencies_bp.route('/<int:currency_id>', methods=['GET'])
@require_auth
def get_currency(currency_id):
    """Get currency by ID"""
    currency = db.session.query(Currency).filter_by(
        id=currency_id,
        user_id=g.user_id
    ).first()

    if not currency:
        return jsonify({'status': 'error', 'message': 'Currency not found'}), 404

    return jsonify({
        'status': 'success',
        'data': currency.to_dict()
    }), 200


@currencies_bp.route('', methods=['POST'])
@require_auth
def create_currency():
    """
    Create new currency

    Request body:
    {
        "name": "Euro",
        "code": "EUR",
        "symbol": "€",
        "rate": 1.0
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Validate required fields
    required = ['name', 'code', 'symbol', 'rate']
    for field in required:
        if field not in data:
            return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400

    # Check if currency code already exists for this user
    existing = db.session.query(Currency).filter_by(
        user_id=g.user_id,
        code=data['code']
    ).first()

    if existing:
        return jsonify({'status': 'error', 'message': 'Currency code already exists'}), 400

    # Validate rate
    try:
        rate = float(data['rate'])
        if rate <= 0:
            return jsonify({'status': 'error', 'message': 'Rate must be positive'}), 400
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid rate value'}), 400

    # Create currency
    currency = Currency(
        user_id=g.user_id,
        name=data['name'],
        code=data['code'].upper(),
        symbol=data['symbol'],
        rate=rate
    )

    db.session.add(currency)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'data': currency.to_dict(),
        'message': 'Currency created successfully'
    }), 201


@currencies_bp.route('/<int:currency_id>', methods=['PUT'])
@require_auth
def update_currency(currency_id):
    """
    Update currency

    Request body:
    {
        "name": "Euro Updated",
        "symbol": "€",
        "rate": 1.1
    }
    """
    currency = db.session.query(Currency).filter_by(
        id=currency_id,
        user_id=g.user_id
    ).first()

    if not currency:
        return jsonify({'status': 'error', 'message': 'Currency not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Update allowed fields (code cannot be changed)
    if 'name' in data:
        currency.name = data['name']
    if 'symbol' in data:
        currency.symbol = data['symbol']
    if 'rate' in data:
        try:
            rate = float(data['rate'])
            if rate <= 0:
                return jsonify({'status': 'error', 'message': 'Rate must be positive'}), 400
            currency.rate = rate
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid rate value'}), 400

    db.session.commit()

    return jsonify({
        'status': 'success',
        'data': currency.to_dict(),
        'message': 'Currency updated successfully'
    }), 200


@currencies_bp.route('/<int:currency_id>', methods=['DELETE'])
@require_auth
def delete_currency(currency_id):
    """Delete currency"""
    currency = db.session.query(Currency).filter_by(
        id=currency_id,
        user_id=g.user_id
    ).first()

    if not currency:
        return jsonify({'status': 'error', 'message': 'Currency not found'}), 404

    # Check if currency is being used as main currency
    user = db.session.get(User, g.user_id)
    if user.main_currency == currency_id:
        return jsonify({
            'status': 'error',
            'message': 'Cannot delete main currency. Please set a different main currency first.'
        }), 400

    # Check if currency is being used by subscriptions
    from app.models.subscription import Subscription
    subscriptions_count = db.session.query(Subscription).filter_by(
        currency_id=currency_id
    ).count()

    if subscriptions_count > 0:
        return jsonify({
            'status': 'error',
            'message': f'Cannot delete currency. {subscriptions_count} subscription(s) are using it.'
        }), 400

    db.session.delete(currency)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Currency deleted successfully'
    }), 200


@currencies_bp.route('/convert', methods=['POST'])
@require_auth
def convert_currency():
    """
    Convert amount between currencies

    Request body:
    {
        "amount": 100,
        "from_currency_id": 1,
        "to_currency_id": 2
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Validate required fields
    required = ['amount', 'from_currency_id', 'to_currency_id']
    for field in required:
        if field not in data:
            return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400

    try:
        amount = float(data['amount'])
        converted = CurrencyConverter.convert(
            amount,
            data['from_currency_id'],
            data['to_currency_id']
        )

        from_currency = db.session.get(Currency, data['from_currency_id'])
        to_currency = db.session.get(Currency, data['to_currency_id'])

        return jsonify({
            'status': 'success',
            'data': {
                'original_amount': amount,
                'converted_amount': round(converted, 2),
                'from_currency': from_currency.to_dict() if from_currency else None,
                'to_currency': to_currency.to_dict() if to_currency else None
            }
        }), 200

    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Conversion failed: {str(e)}'}), 500
