"""
Budget API Endpoints
"""
from flask import Blueprint, request, jsonify, g
from app import db
from app.models.user import User
from app.services.budget_analyzer import BudgetAnalyzer
from app.utils.decorators import require_auth

budget_bp = Blueprint('budget', __name__)


@budget_bp.route('', methods=['GET'])
@require_auth
def get_budget():
    """
    Get budget status for current user

    Returns comprehensive budget information including:
    - Monthly budget
    - Current spending
    - Budget utilization %
    - Remaining budget
    - Projected yearly cost
    - Savings from inactive subscriptions
    """
    budget_status = BudgetAnalyzer.get_budget_status(g.user_id)

    return jsonify({
        'status': 'success',
        'data': budget_status
    }), 200


@budget_bp.route('', methods=['PUT'])
@require_auth
def update_budget():
    """
    Update monthly budget

    Request body:
    {
        "monthly_budget": 200.00
    }
    """
    data = request.get_json()

    if not data or 'monthly_budget' not in data:
        return jsonify({'status': 'error', 'message': 'monthly_budget is required'}), 400

    budget = data['monthly_budget']

    if not isinstance(budget, (int, float)) or budget < 0:
        return jsonify({'status': 'error', 'message': 'Budget must be a positive number'}), 400

    # Update user budget
    user = db.session.get(User, g.user_id)
    user.budget = budget
    db.session.commit()

    # Return updated budget status
    budget_status = BudgetAnalyzer.get_budget_status(g.user_id)

    return jsonify({
        'status': 'success',
        'data': budget_status,
        'message': 'Budget updated successfully'
    }), 200


@budget_bp.route('/breakdown', methods=['GET'])
@require_auth
def get_breakdown():
    """
    Get spending breakdown by category

    Returns:
    {
        "Entertainment": 45.99,
        "Productivity": 20.00,
        "Cloud Storage": 10.00
    }
    """
    breakdown = BudgetAnalyzer.get_spending_by_category(g.user_id)

    return jsonify({
        'status': 'success',
        'data': breakdown
    }), 200


@budget_bp.route('/upcoming', methods=['GET'])
@require_auth
def get_upcoming():
    """
    Get upcoming payments

    Query parameters:
    - days: Number of days to look ahead (default: 7)
    """
    days = request.args.get('days', 7, type=int)

    if days < 1 or days > 365:
        return jsonify({'status': 'error', 'message': 'Days must be between 1 and 365'}), 400

    upcoming = BudgetAnalyzer.get_upcoming_payments(g.user_id, days)

    return jsonify({
        'status': 'success',
        'data': upcoming,
        'count': len(upcoming)
    }), 200
