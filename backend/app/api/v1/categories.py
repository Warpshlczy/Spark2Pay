"""
Category API Endpoints
"""
from flask import Blueprint, request, jsonify, g
from app import db
from app.models.category import Category
from app.utils.decorators import require_auth

categories_bp = Blueprint('categories', __name__)


@categories_bp.route('', methods=['GET'])
@require_auth
def list_categories():
    """
    List all categories for current user

    Query parameters:
    - sort: Sort field (name, order)
    - order: Sort order (asc, desc)
    """
    sort = request.args.get('sort', 'order')
    order = request.args.get('order', 'asc')

    query = db.session.query(Category).filter_by(user_id=g.user_id)

    # Sort
    if hasattr(Category, sort):
        sort_column = getattr(Category, sort)
        if order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

    categories = query.all()

    return jsonify({
        'status': 'success',
        'data': [category.to_dict() for category in categories],
        'total': len(categories)
    }), 200


@categories_bp.route('/<int:category_id>', methods=['GET'])
@require_auth
def get_category(category_id):
    """Get category by ID"""
    category = db.session.query(Category).filter_by(
        id=category_id,
        user_id=g.user_id
    ).first()

    if not category:
        return jsonify({'status': 'error', 'message': 'Category not found'}), 404

    return jsonify({
        'status': 'success',
        'data': category.to_dict()
    }), 200


@categories_bp.route('', methods=['POST'])
@require_auth
def create_category():
    """
    Create new category

    Request body:
    {
        "name": "Entertainment",
        "order": 1
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Validate required fields
    if 'name' not in data:
        return jsonify({'status': 'error', 'message': 'name is required'}), 400

    # Check if category name already exists for this user
    existing = db.session.query(Category).filter_by(
        user_id=g.user_id,
        name=data['name']
    ).first()

    if existing:
        return jsonify({'status': 'error', 'message': 'Category name already exists'}), 400

    # Get next order if not provided
    order = data.get('order')
    if order is None:
        max_order = db.session.query(db.func.max(Category.order)).filter_by(
            user_id=g.user_id
        ).scalar()
        order = (max_order or 0) + 1

    # Create category
    category = Category(
        user_id=g.user_id,
        name=data['name'],
        order=order
    )

    db.session.add(category)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'data': category.to_dict(),
        'message': 'Category created successfully'
    }), 201


@categories_bp.route('/<int:category_id>', methods=['PUT'])
@require_auth
def update_category(category_id):
    """
    Update category

    Request body:
    {
        "name": "Entertainment Updated",
        "order": 2
    }
    """
    category = db.session.query(Category).filter_by(
        id=category_id,
        user_id=g.user_id
    ).first()

    if not category:
        return jsonify({'status': 'error', 'message': 'Category not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Check for duplicate name
    if 'name' in data and data['name'] != category.name:
        existing = db.session.query(Category).filter_by(
            user_id=g.user_id,
            name=data['name']
        ).first()
        if existing:
            return jsonify({'status': 'error', 'message': 'Category name already exists'}), 400

    # Update allowed fields
    if 'name' in data:
        category.name = data['name']
    if 'order' in data:
        category.order = data['order']

    db.session.commit()

    return jsonify({
        'status': 'success',
        'data': category.to_dict(),
        'message': 'Category updated successfully'
    }), 200


@categories_bp.route('/<int:category_id>', methods=['DELETE'])
@require_auth
def delete_category(category_id):
    """Delete category"""
    category = db.session.query(Category).filter_by(
        id=category_id,
        user_id=g.user_id
    ).first()

    if not category:
        return jsonify({'status': 'error', 'message': 'Category not found'}), 404

    # Check if category is being used by subscriptions
    from app.models.subscription import Subscription
    subscriptions_count = db.session.query(Subscription).filter_by(
        category_id=category_id
    ).count()

    if subscriptions_count > 0:
        return jsonify({
            'status': 'error',
            'message': f'Cannot delete category. {subscriptions_count} subscription(s) are using it.'
        }), 400

    db.session.delete(category)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Category deleted successfully'
    }), 200
