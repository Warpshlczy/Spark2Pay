"""
Statistics and Analytics API Endpoints
"""
from flask import Blueprint, request, jsonify, g
from app.services.statistics_service import StatisticsService
from app.utils.decorators import require_auth

statistics_bp = Blueprint('statistics', __name__)


@statistics_bp.route('/overview', methods=['GET'])
@require_auth
def get_overview():
    """
    Get overview statistics

    Returns:
    - Active/inactive subscription counts
    - Total monthly and yearly costs
    - Average subscription cost
    """
    overview = StatisticsService.get_overview(g.user_id)

    return jsonify({
        'status': 'success',
        'data': overview
    }), 200


@statistics_bp.route('/by-category', methods=['GET'])
@require_auth
def get_by_category():
    """
    Get spending breakdown by category

    Returns spending data grouped by category
    """
    data = StatisticsService.get_by_category(g.user_id)

    return jsonify({
        'status': 'success',
        'data': data,
        'total': len(data)
    }), 200


@statistics_bp.route('/by-payment-method', methods=['GET'])
@require_auth
def get_by_payment_method():
    """
    Get spending breakdown by payment method

    Returns spending data grouped by payment method
    """
    data = StatisticsService.get_by_payment_method(g.user_id)

    return jsonify({
        'status': 'success',
        'data': data,
        'total': len(data)
    }), 200


@statistics_bp.route('/trends', methods=['GET'])
@require_auth
def get_trends():
    """
    Get spending trends over time

    Query parameters:
    - months: Number of months to analyze (default: 6)
    """
    months = request.args.get('months', 6, type=int)

    if months < 1 or months > 24:
        return jsonify({'status': 'error', 'message': 'Months must be between 1 and 24'}), 400

    trends = StatisticsService.get_trends(g.user_id, months)

    return jsonify({
        'status': 'success',
        'data': trends
    }), 200


@statistics_bp.route('/upcoming-renewals', methods=['GET'])
@require_auth
def get_upcoming_renewals():
    """
    Get upcoming subscription renewals

    Query parameters:
    - days: Number of days to look ahead (default: 30)
    """
    days = request.args.get('days', 30, type=int)

    if days < 1 or days > 365:
        return jsonify({'status': 'error', 'message': 'Days must be between 1 and 365'}), 400

    renewals = StatisticsService.get_upcoming_renewals(g.user_id, days)

    return jsonify({
        'status': 'success',
        'data': renewals,
        'total': len(renewals)
    }), 200


@statistics_bp.route('/most-expensive', methods=['GET'])
@require_auth
def get_most_expensive():
    """
    Get most expensive subscriptions

    Query parameters:
    - limit: Number of subscriptions to return (default: 5)
    """
    limit = request.args.get('limit', 5, type=int)

    if limit < 1 or limit > 50:
        return jsonify({'status': 'error', 'message': 'Limit must be between 1 and 50'}), 400

    expensive = StatisticsService.get_most_expensive(g.user_id, limit)

    return jsonify({
        'status': 'success',
        'data': expensive,
        'total': len(expensive)
    }), 200
