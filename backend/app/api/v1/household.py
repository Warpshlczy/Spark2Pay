"""
Household Member API Endpoints
"""
from flask import Blueprint, request, jsonify, g
from app import db
from app.models.household import HouseholdMember
from app.utils.decorators import require_auth

household_bp = Blueprint('household', __name__)


@household_bp.route('', methods=['GET'])
@require_auth
def list_household_members():
    """
    List all household members for current user

    Query parameters:
    - sort: Sort field (name, email)
    - order: Sort order (asc, desc)
    """
    sort = request.args.get('sort', 'name')
    order = request.args.get('order', 'asc')

    query = db.session.query(HouseholdMember).filter_by(user_id=g.user_id)

    # Sort
    if hasattr(HouseholdMember, sort):
        sort_column = getattr(HouseholdMember, sort)
        if order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

    members = query.all()

    return jsonify({
        'status': 'success',
        'data': [member.to_dict() for member in members],
        'total': len(members)
    }), 200


@household_bp.route('/<int:member_id>', methods=['GET'])
@require_auth
def get_household_member(member_id):
    """Get household member by ID"""
    member = db.session.query(HouseholdMember).filter_by(
        id=member_id,
        user_id=g.user_id
    ).first()

    if not member:
        return jsonify({'status': 'error', 'message': 'Household member not found'}), 404

    return jsonify({
        'status': 'success',
        'data': member.to_dict()
    }), 200


@household_bp.route('', methods=['POST'])
@require_auth
def create_household_member():
    """
    Create new household member

    Request body:
    {
        "name": "John Doe",
        "email": "john@example.com"
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Validate required fields
    if 'name' not in data:
        return jsonify({'status': 'error', 'message': 'name is required'}), 400

    # Create household member
    member = HouseholdMember(
        user_id=g.user_id,
        name=data['name'],
        email=data.get('email')
    )

    db.session.add(member)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'data': member.to_dict(),
        'message': 'Household member created successfully'
    }), 201


@household_bp.route('/<int:member_id>', methods=['PUT'])
@require_auth
def update_household_member(member_id):
    """
    Update household member

    Request body:
    {
        "name": "John Doe Updated",
        "email": "john.updated@example.com"
    }
    """
    member = db.session.query(HouseholdMember).filter_by(
        id=member_id,
        user_id=g.user_id
    ).first()

    if not member:
        return jsonify({'status': 'error', 'message': 'Household member not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Update allowed fields
    if 'name' in data:
        member.name = data['name']
    if 'email' in data:
        member.email = data['email']

    db.session.commit()

    return jsonify({
        'status': 'success',
        'data': member.to_dict(),
        'message': 'Household member updated successfully'
    }), 200


@household_bp.route('/<int:member_id>', methods=['DELETE'])
@require_auth
def delete_household_member(member_id):
    """Delete household member"""
    member = db.session.query(HouseholdMember).filter_by(
        id=member_id,
        user_id=g.user_id
    ).first()

    if not member:
        return jsonify({'status': 'error', 'message': 'Household member not found'}), 404

    db.session.delete(member)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Household member deleted successfully'
    }), 200
