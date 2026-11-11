"""
Calendar View API Endpoints
"""
from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from calendar import monthrange
from app import db
from app.models.subscription import Subscription
from app.utils.decorators import require_auth

calendar_bp = Blueprint('calendar', __name__)


@calendar_bp.route('', methods=['GET'])
@require_auth
def get_calendar():
    """
    Get calendar view of subscription payments

    Query parameters:
    - year: Year (default: current year)
    - month: Month (1-12, default: current month)

    Returns calendar with subscription payment dates
    """
    # Get current date defaults
    now = datetime.now()
    year = request.args.get('year', now.year, type=int)
    month = request.args.get('month', now.month, type=int)

    # Validate inputs
    if year < 2000 or year > 2100:
        return jsonify({'status': 'error', 'message': 'Year must be between 2000 and 2100'}), 400

    if month < 1 or month > 12:
        return jsonify({'status': 'error', 'message': 'Month must be between 1 and 12'}), 400

    # Get first and last day of month
    first_day = datetime(year, month, 1).date()
    _, last_day_num = monthrange(year, month)
    last_day = datetime(year, month, last_day_num).date()

    # Get all subscriptions with payments in this month
    subscriptions = db.session.query(Subscription).filter(
        Subscription.user_id == g.user_id,
        Subscription.inactive == False,
        Subscription.next_payment >= first_day,
        Subscription.next_payment <= last_day
    ).all()

    # Build calendar data
    calendar_data = {}

    for sub in subscriptions:
        day = sub.next_payment.day
        day_key = str(day)

        if day_key not in calendar_data:
            calendar_data[day_key] = {
                'day': day,
                'date': sub.next_payment.isoformat(),
                'subscriptions': []
            }

        # Get currency symbol
        currency_symbol = '$'
        if sub.currency:
            currency_symbol = sub.currency.symbol

        calendar_data[day_key]['subscriptions'].append({
            'id': sub.id,
            'name': sub.name,
            'price': sub.price,
            'currency_symbol': currency_symbol,
            'logo': sub.logo,
            'category': sub.category.name if sub.category else None
        })

    # Convert to list and sort by day
    result = list(calendar_data.values())
    result.sort(key=lambda x: x['day'])

    return jsonify({
        'status': 'success',
        'data': {
            'year': year,
            'month': month,
            'month_name': datetime(year, month, 1).strftime('%B'),
            'days_in_month': last_day_num,
            'first_day': first_day.isoformat(),
            'last_day': last_day.isoformat(),
            'payment_days': result,
            'total_payment_days': len(result)
        }
    }), 200


@calendar_bp.route('/upcoming', methods=['GET'])
@require_auth
def get_upcoming():
    """
    Get upcoming payments in next N days

    Query parameters:
    - days: Number of days to look ahead (default: 7)

    Returns list of upcoming subscription payments
    """
    days = request.args.get('days', 7, type=int)

    if days < 1 or days > 365:
        return jsonify({'status': 'error', 'message': 'Days must be between 1 and 365'}), 400

    today = datetime.now().date()
    end_date = today + timedelta(days=days)

    subscriptions = db.session.query(Subscription).filter(
        Subscription.user_id == g.user_id,
        Subscription.inactive == False,
        Subscription.next_payment >= today,
        Subscription.next_payment <= end_date
    ).order_by(Subscription.next_payment).all()

    result = []
    for sub in subscriptions:
        days_until = (sub.next_payment - today).days

        # Get currency symbol
        currency_symbol = '$'
        if sub.currency:
            currency_symbol = sub.currency.symbol

        result.append({
            'subscription': sub.to_dict(),
            'days_until': days_until,
            'is_today': days_until == 0,
            'is_tomorrow': days_until == 1
        })

    return jsonify({
        'status': 'success',
        'data': result,
        'total': len(result),
        'days_ahead': days
    }), 200


@calendar_bp.route('/year-view', methods=['GET'])
@require_auth
def get_year_view():
    """
    Get year view with monthly totals

    Query parameters:
    - year: Year (default: current year)

    Returns monthly payment totals for the year
    """
    year = request.args.get('year', datetime.now().year, type=int)

    if year < 2000 or year > 2100:
        return jsonify({'status': 'error', 'message': 'Year must be between 2000 and 2100'}), 400

    # Get all active subscriptions
    subscriptions = db.session.query(Subscription).filter_by(
        user_id=g.user_id,
        inactive=False
    ).all()

    # Build year view
    monthly_data = []

    for month_num in range(1, 13):
        first_day = datetime(year, month_num, 1).date()
        _, last_day_num = monthrange(year, month_num)
        last_day = datetime(year, month_num, last_day_num).date()

        # Count subscriptions and calculate total for this month
        month_subscriptions = []
        total_cost = 0.0

        for sub in subscriptions:
            if sub.next_payment and first_day <= sub.next_payment <= last_day:
                month_subscriptions.append({
                    'id': sub.id,
                    'name': sub.name,
                    'price': sub.price,
                    'payment_date': sub.next_payment.isoformat()
                })
                total_cost += sub.price

        monthly_data.append({
            'month': month_num,
            'month_name': datetime(year, month_num, 1).strftime('%B'),
            'subscription_count': len(month_subscriptions),
            'total_cost': round(total_cost, 2),
            'subscriptions': month_subscriptions
        })

    return jsonify({
        'status': 'success',
        'data': {
            'year': year,
            'months': monthly_data,
            'total_yearly_payments': sum(m['subscription_count'] for m in monthly_data)
        }
    }), 200
