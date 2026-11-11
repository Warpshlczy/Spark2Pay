"""
Statistics and Analytics Service
Provides insights and analytics on subscription data
"""
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models.subscription import Subscription
from app.models.currency import Currency
from app.models.category import Category
from app.models.payment_method import PaymentMethod
from app.models.user import User
from app.services.billing_cycle import BillingCycleCalculator
from app.services.currency_converter import CurrencyConverter


class StatisticsService:
    """Generate statistics and analytics for subscriptions"""

    @staticmethod
    def get_overview(user_id: int) -> dict:
        """
        Get overview statistics

        Args:
            user_id: User ID

        Returns:
            Dictionary with overview metrics
        """
        user = db.session.get(User, user_id)

        # Count active and inactive subscriptions
        active_count = db.session.query(Subscription).filter_by(
            user_id=user_id,
            inactive=False
        ).count()

        inactive_count = db.session.query(Subscription).filter_by(
            user_id=user_id,
            inactive=True
        ).count()

        # Calculate total monthly cost
        subscriptions = db.session.query(Subscription).filter_by(
            user_id=user_id,
            inactive=False
        ).all()

        total_monthly = 0.0
        for sub in subscriptions:
            monthly_cost = BillingCycleCalculator.calculate_monthly_cost(
                sub.price,
                sub.cycle,
                sub.frequency
            )

            # Convert to main currency
            if user and user.main_currency and sub.currency_id != user.main_currency:
                try:
                    monthly_cost = CurrencyConverter.convert(
                        monthly_cost,
                        sub.currency_id,
                        user.main_currency
                    )
                except ValueError:
                    pass

            total_monthly += monthly_cost

        # Calculate average subscription cost
        avg_monthly = total_monthly / active_count if active_count > 0 else 0

        # Get main currency symbol
        currency_symbol = '$'
        if user and user.main_currency:
            currency = db.session.get(Currency, user.main_currency)
            if currency:
                currency_symbol = currency.symbol

        return {
            'active_subscriptions': active_count,
            'inactive_subscriptions': inactive_count,
            'total_subscriptions': active_count + inactive_count,
            'total_monthly_cost': round(total_monthly, 2),
            'total_yearly_cost': round(total_monthly * 12, 2),
            'average_subscription_cost': round(avg_monthly, 2),
            'currency_symbol': currency_symbol
        }

    @staticmethod
    def get_by_category(user_id: int) -> list:
        """
        Get spending breakdown by category

        Args:
            user_id: User ID

        Returns:
            List of category spending data
        """
        user = db.session.get(User, user_id)
        subscriptions = db.session.query(Subscription).filter_by(
            user_id=user_id,
            inactive=False
        ).all()

        category_data = {}

        for sub in subscriptions:
            category_name = sub.category.name if sub.category else 'Uncategorized'
            category_id = sub.category_id if sub.category else None

            monthly_cost = BillingCycleCalculator.calculate_monthly_cost(
                sub.price,
                sub.cycle,
                sub.frequency
            )

            # Convert to main currency
            if user and user.main_currency and sub.currency_id != user.main_currency:
                try:
                    monthly_cost = CurrencyConverter.convert(
                        monthly_cost,
                        sub.currency_id,
                        user.main_currency
                    )
                except ValueError:
                    pass

            if category_name not in category_data:
                category_data[category_name] = {
                    'category_id': category_id,
                    'category_name': category_name,
                    'monthly_cost': 0.0,
                    'yearly_cost': 0.0,
                    'subscription_count': 0
                }

            category_data[category_name]['monthly_cost'] += monthly_cost
            category_data[category_name]['yearly_cost'] += monthly_cost * 12
            category_data[category_name]['subscription_count'] += 1

        # Round values and convert to list
        result = []
        for data in category_data.values():
            data['monthly_cost'] = round(data['monthly_cost'], 2)
            data['yearly_cost'] = round(data['yearly_cost'], 2)
            result.append(data)

        # Sort by monthly cost descending
        result.sort(key=lambda x: x['monthly_cost'], reverse=True)

        return result

    @staticmethod
    def get_by_payment_method(user_id: int) -> list:
        """
        Get spending breakdown by payment method

        Args:
            user_id: User ID

        Returns:
            List of payment method spending data
        """
        user = db.session.get(User, user_id)
        subscriptions = db.session.query(Subscription).filter_by(
            user_id=user_id,
            inactive=False
        ).all()

        payment_method_data = {}

        for sub in subscriptions:
            pm_name = sub.payment_method.name if sub.payment_method else 'No Payment Method'
            pm_id = sub.payment_method_id if sub.payment_method else None

            monthly_cost = BillingCycleCalculator.calculate_monthly_cost(
                sub.price,
                sub.cycle,
                sub.frequency
            )

            # Convert to main currency
            if user and user.main_currency and sub.currency_id != user.main_currency:
                try:
                    monthly_cost = CurrencyConverter.convert(
                        monthly_cost,
                        sub.currency_id,
                        user.main_currency
                    )
                except ValueError:
                    pass

            if pm_name not in payment_method_data:
                payment_method_data[pm_name] = {
                    'payment_method_id': pm_id,
                    'payment_method_name': pm_name,
                    'monthly_cost': 0.0,
                    'yearly_cost': 0.0,
                    'subscription_count': 0
                }

            payment_method_data[pm_name]['monthly_cost'] += monthly_cost
            payment_method_data[pm_name]['yearly_cost'] += monthly_cost * 12
            payment_method_data[pm_name]['subscription_count'] += 1

        # Round values and convert to list
        result = []
        for data in payment_method_data.values():
            data['monthly_cost'] = round(data['monthly_cost'], 2)
            data['yearly_cost'] = round(data['yearly_cost'], 2)
            result.append(data)

        # Sort by monthly cost descending
        result.sort(key=lambda x: x['monthly_cost'], reverse=True)

        return result

    @staticmethod
    def get_trends(user_id: int, months: int = 6) -> dict:
        """
        Get spending trends over time

        Args:
            user_id: User ID
            months: Number of months to analyze

        Returns:
            Dictionary with trend data
        """
        # This would require tracking historical data
        # For now, return current month projection
        user = db.session.get(User, user_id)
        subscriptions = db.session.query(Subscription).filter_by(
            user_id=user_id,
            inactive=False
        ).all()

        total_monthly = 0.0
        for sub in subscriptions:
            monthly_cost = BillingCycleCalculator.calculate_monthly_cost(
                sub.price,
                sub.cycle,
                sub.frequency
            )

            if user and user.main_currency and sub.currency_id != user.main_currency:
                try:
                    monthly_cost = CurrencyConverter.convert(
                        monthly_cost,
                        sub.currency_id,
                        user.main_currency
                    )
                except ValueError:
                    pass

            total_monthly += monthly_cost

        # Generate trend data (simplified - would need historical tracking for real trends)
        trend_data = []
        current_date = datetime.now()

        for i in range(months):
            month_date = current_date - timedelta(days=30 * i)
            trend_data.insert(0, {
                'month': month_date.strftime('%Y-%m'),
                'monthly_cost': round(total_monthly, 2),
                'active_subscriptions': len(subscriptions)
            })

        return {
            'months': months,
            'data': trend_data
        }

    @staticmethod
    def get_upcoming_renewals(user_id: int, days: int = 30) -> list:
        """
        Get upcoming subscription renewals

        Args:
            user_id: User ID
            days: Number of days to look ahead

        Returns:
            List of upcoming renewals
        """
        today = datetime.now().date()
        end_date = today + timedelta(days=days)

        subscriptions = db.session.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.inactive == False,
            Subscription.next_payment >= today,
            Subscription.next_payment <= end_date
        ).order_by(Subscription.next_payment).all()

        result = []
        for sub in subscriptions:
            days_until = (sub.next_payment - today).days
            result.append({
                'subscription': sub.to_dict(),
                'days_until_renewal': days_until
            })

        return result

    @staticmethod
    def get_most_expensive(user_id: int, limit: int = 5) -> list:
        """
        Get most expensive subscriptions

        Args:
            user_id: User ID
            limit: Number of subscriptions to return

        Returns:
            List of most expensive subscriptions
        """
        user = db.session.get(User, user_id)
        subscriptions = db.session.query(Subscription).filter_by(
            user_id=user_id,
            inactive=False
        ).all()

        # Calculate monthly cost for each
        subscription_costs = []
        for sub in subscriptions:
            monthly_cost = BillingCycleCalculator.calculate_monthly_cost(
                sub.price,
                sub.cycle,
                sub.frequency
            )

            # Convert to main currency
            if user and user.main_currency and sub.currency_id != user.main_currency:
                try:
                    monthly_cost = CurrencyConverter.convert(
                        monthly_cost,
                        sub.currency_id,
                        user.main_currency
                    )
                except ValueError:
                    pass

            subscription_costs.append({
                'subscription': sub.to_dict(),
                'monthly_cost': round(monthly_cost, 2),
                'yearly_cost': round(monthly_cost * 12, 2)
            })

        # Sort by monthly cost descending
        subscription_costs.sort(key=lambda x: x['monthly_cost'], reverse=True)

        return subscription_costs[:limit]
