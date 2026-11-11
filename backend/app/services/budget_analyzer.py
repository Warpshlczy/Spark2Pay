"""
Budget Analyzer Service
Analyzes spending and budget utilization
"""
from app import db
from app.models.subscription import Subscription
from app.models.user import User
from app.services.billing_cycle import BillingCycleCalculator
from app.services.currency_converter import CurrencyConverter


class BudgetAnalyzer:
    """Analyze budget and spending"""

    @staticmethod
    def calculate_monthly_spending(user_id: int) -> float:
        """
        Calculate total monthly spending for user

        Converts all subscriptions to monthly equivalents in user's main currency

        Args:
            user_id: User ID

        Returns:
            Total monthly spending
        """
        user = db.session.get(User, user_id)
        if not user:
            return 0.0

        subscriptions = db.session.query(Subscription).filter_by(
            user_id=user_id,
            inactive=False
        ).all()

        total = 0.0

        for sub in subscriptions:
            # Calculate monthly cost
            monthly_cost = BillingCycleCalculator.calculate_monthly_cost(
                sub.price,
                sub.cycle,
                sub.frequency
            )

            # Convert to user's main currency if different
            if user.main_currency and sub.currency_id != user.main_currency:
                try:
                    monthly_cost = CurrencyConverter.convert(
                        monthly_cost,
                        sub.currency_id,
                        user.main_currency
                    )
                except ValueError:
                    # If conversion fails, use original cost
                    pass

            total += monthly_cost

        return round(total, 2)

    @staticmethod
    def get_budget_status(user_id: int) -> dict:
        """
        Get comprehensive budget status

        Args:
            user_id: User ID

        Returns:
            Dictionary with budget information
        """
        user = db.session.get(User, user_id)
        if not user:
            return {
                'monthly_budget': 0,
                'current_spending': 0,
                'utilization': 0,
                'remaining': 0,
                'projected_yearly': 0
            }

        monthly_spending = BudgetAnalyzer.calculate_monthly_spending(user_id)
        budget = user.budget or 0

        utilization = (monthly_spending / budget * 100) if budget > 0 else 0
        remaining = budget - monthly_spending
        projected_yearly = monthly_spending * 12

        return {
            'monthly_budget': round(budget, 2),
            'current_spending': round(monthly_spending, 2),
            'utilization': round(utilization, 2),
            'remaining': round(remaining, 2),
            'projected_yearly': round(projected_yearly, 2),
            'savings_from_inactive': BudgetAnalyzer.calculate_savings_from_inactive(user_id)
        }

    @staticmethod
    def calculate_savings_from_inactive(user_id: int) -> float:
        """
        Calculate monthly savings from inactive subscriptions

        Args:
            user_id: User ID

        Returns:
            Monthly savings amount
        """
        user = db.session.get(User, user_id)
        inactive_subs = db.session.query(Subscription).filter_by(
            user_id=user_id,
            inactive=True
        ).all()

        total_savings = 0.0

        for sub in inactive_subs:
            monthly_cost = BillingCycleCalculator.calculate_monthly_cost(
                sub.price,
                sub.cycle,
                sub.frequency
            )

            # Convert to main currency if needed
            if user and user.main_currency and sub.currency_id != user.main_currency:
                try:
                    monthly_cost = CurrencyConverter.convert(
                        monthly_cost,
                        sub.currency_id,
                        user.main_currency
                    )
                except ValueError:
                    pass

            total_savings += monthly_cost

        return round(total_savings, 2)

    @staticmethod
    def get_spending_by_category(user_id: int) -> dict:
        """
        Get spending breakdown by category

        Args:
            user_id: User ID

        Returns:
            Dictionary of category_name -> monthly_cost
        """
        user = db.session.get(User, user_id)
        subscriptions = db.session.query(Subscription).filter_by(
            user_id=user_id,
            inactive=False
        ).all()

        category_spending = {}

        for sub in subscriptions:
            category_name = sub.category.name if sub.category else 'Uncategorized'

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

            if category_name not in category_spending:
                category_spending[category_name] = 0.0

            category_spending[category_name] += monthly_cost

        # Round all values
        return {k: round(v, 2) for k, v in category_spending.items()}

    @staticmethod
    def get_upcoming_payments(user_id: int, days: int = 7) -> list:
        """
        Get upcoming payments in next N days

        Args:
            user_id: User ID
            days: Number of days to look ahead

        Returns:
            List of subscriptions with upcoming payments
        """
        from datetime import datetime, timedelta

        today = datetime.now().date()
        end_date = today + timedelta(days=days)

        subscriptions = db.session.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.inactive == False,
            Subscription.next_payment >= today,
            Subscription.next_payment <= end_date
        ).order_by(Subscription.next_payment).all()

        return [sub.to_dict() for sub in subscriptions]
