"""
Billing Cycle Calculator
Handles subscription billing cycle calculations and next payment dates
"""
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional


class BillingCycleCalculator:
    """Calculate billing cycles and payment dates"""

    # Billing cycle constants
    CYCLE_DAYS = 1
    CYCLE_WEEKS = 2
    CYCLE_MONTHS = 3
    CYCLE_YEARS = 4

    @staticmethod
    def calculate_next_payment(
        start_date: datetime,
        cycle: int,
        frequency: int
    ) -> datetime:
        """
        Calculate next payment date based on cycle and frequency

        Args:
            start_date: Starting date (usually today or last payment)
            cycle: Billing cycle type (1=days, 2=weeks, 3=months, 4=years)
            frequency: How many cycles (e.g., every 2 months)

        Returns:
            Next payment date

        Raises:
            ValueError: If cycle is invalid
        """
        if cycle == BillingCycleCalculator.CYCLE_DAYS:
            return start_date + timedelta(days=frequency)

        elif cycle == BillingCycleCalculator.CYCLE_WEEKS:
            return start_date + timedelta(weeks=frequency)

        elif cycle == BillingCycleCalculator.CYCLE_MONTHS:
            return start_date + relativedelta(months=frequency)

        elif cycle == BillingCycleCalculator.CYCLE_YEARS:
            return start_date + relativedelta(years=frequency)

        else:
            raise ValueError(f"Invalid cycle: {cycle}. Must be 1 (days), 2 (weeks), 3 (months), or 4 (years)")

    @staticmethod
    def calculate_monthly_cost(price: float, cycle: int, frequency: int) -> float:
        """
        Convert subscription price to monthly equivalent

        Args:
            price: Subscription price
            cycle: Billing cycle type
            frequency: How many cycles

        Returns:
            Monthly cost equivalent

        Examples:
            $30 every 3 months = $10/month
            $120 yearly = $10/month
            $10 weekly = $43.33/month
        """
        if cycle == BillingCycleCalculator.CYCLE_DAYS:
            # Average days per month = 365.25 / 12 = 30.44
            return (price / frequency) * 30.44

        elif cycle == BillingCycleCalculator.CYCLE_WEEKS:
            # Average weeks per month = 52 / 12 = 4.33
            return (price / frequency) * 4.33

        elif cycle == BillingCycleCalculator.CYCLE_MONTHS:
            return price / frequency

        elif cycle == BillingCycleCalculator.CYCLE_YEARS:
            return price / (frequency * 12)

        else:
            raise ValueError(f"Invalid cycle: {cycle}")

    @staticmethod
    def calculate_yearly_cost(price: float, cycle: int, frequency: int) -> float:
        """
        Convert subscription price to yearly equivalent

        Args:
            price: Subscription price
            cycle: Billing cycle type
            frequency: How many cycles

        Returns:
            Yearly cost equivalent
        """
        monthly_cost = BillingCycleCalculator.calculate_monthly_cost(price, cycle, frequency)
        return monthly_cost * 12

    @staticmethod
    def get_cycle_name(cycle: int, frequency: int) -> str:
        """
        Get human-readable cycle name

        Args:
            cycle: Billing cycle type
            frequency: How many cycles

        Returns:
            Human-readable string (e.g., "Every 2 months", "Weekly")
        """
        if frequency == 1:
            names = {
                BillingCycleCalculator.CYCLE_DAYS: "Daily",
                BillingCycleCalculator.CYCLE_WEEKS: "Weekly",
                BillingCycleCalculator.CYCLE_MONTHS: "Monthly",
                BillingCycleCalculator.CYCLE_YEARS: "Yearly"
            }
            return names.get(cycle, "Unknown")
        else:
            names = {
                BillingCycleCalculator.CYCLE_DAYS: f"Every {frequency} days",
                BillingCycleCalculator.CYCLE_WEEKS: f"Every {frequency} weeks",
                BillingCycleCalculator.CYCLE_MONTHS: f"Every {frequency} months",
                BillingCycleCalculator.CYCLE_YEARS: f"Every {frequency} years"
            }
            return names.get(cycle, "Unknown")

    @staticmethod
    def days_until_payment(next_payment: datetime) -> int:
        """
        Calculate days until next payment

        Args:
            next_payment: Next payment date

        Returns:
            Number of days until payment (negative if overdue)
        """
        today = datetime.now().date()
        if isinstance(next_payment, datetime):
            next_payment = next_payment.date()

        delta = next_payment - today
        return delta.days
