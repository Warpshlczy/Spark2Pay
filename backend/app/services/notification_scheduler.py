"""
Notification Scheduler
Background jobs for automatic notifications
"""
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app import db
from app.models.subscription import Subscription
from app.models.user import User
from app.services.notifications.notification_manager import NotificationManager
from app.services.currency_converter import CurrencyConverter


class NotificationScheduler:
    """Scheduler for automatic subscription notifications"""

    def __init__(self, app=None):
        """
        Initialize scheduler

        Args:
            app: Flask application instance
        """
        self.scheduler = BackgroundScheduler()
        self.app = app

        if app:
            self.init_app(app)

    def init_app(self, app):
        """
        Initialize with Flask app

        Args:
            app: Flask application instance
        """
        self.app = app

        # Schedule jobs
        self.schedule_jobs()

        # Start scheduler
        if not self.scheduler.running:
            self.scheduler.start()

    def schedule_jobs(self):
        """Schedule all background jobs"""

        # Daily job at 9:00 AM for upcoming payment notifications
        self.scheduler.add_job(
            func=self.send_upcoming_payment_notifications,
            trigger=CronTrigger(hour=9, minute=0),
            id='upcoming_payments',
            name='Send upcoming payment notifications',
            replace_existing=True
        )

        # Daily job at 8:00 AM for overdue payment notifications
        self.scheduler.add_job(
            func=self.send_overdue_notifications,
            trigger=CronTrigger(hour=8, minute=0),
            id='overdue_payments',
            name='Send overdue payment notifications',
            replace_existing=True
        )

        # Daily job at 10:00 AM for cancellation reminders
        self.scheduler.add_job(
            func=self.send_cancellation_reminders,
            trigger=CronTrigger(hour=10, minute=0),
            id='cancellation_reminders',
            name='Send cancellation reminders',
            replace_existing=True
        )

        # Daily job at 2:00 AM for currency rate updates
        self.scheduler.add_job(
            func=self.update_currency_rates,
            trigger=CronTrigger(hour=2, minute=0),
            id='currency_updates',
            name='Update currency exchange rates',
            replace_existing=True
        )

        print("✅ Notification scheduler jobs configured:")
        print("  - Upcoming payments: Daily at 9:00 AM")
        print("  - Overdue payments: Daily at 8:00 AM")
        print("  - Cancellation reminders: Daily at 10:00 AM")
        print("  - Currency updates: Daily at 2:00 AM")

    def send_upcoming_payment_notifications(self):
        """
        Send notifications for upcoming payments

        Checks all active subscriptions and sends notifications based on
        user's notify_days_before setting
        """
        with self.app.app_context():
            try:
                today = datetime.now().date()

                # Get all active subscriptions
                subscriptions = db.session.query(Subscription).filter_by(inactive=False).all()

                notifications_sent = 0

                for sub in subscriptions:
                    if not sub.next_payment:
                        continue

                    # Calculate days until payment
                    days_until = (sub.next_payment - today).days

                    # Check if we should notify
                    if days_until == sub.notify_days_before:
                        # Get user's currency
                        user = db.session.get(User, sub.user_id)
                        currency_symbol = '$'

                        if sub.currency:
                            currency_symbol = sub.currency.symbol

                        # Prepare subscription data
                        subscription_data = {
                            'name': sub.name,
                            'price': sub.price,
                            'currency_symbol': currency_symbol,
                            'next_payment': sub.next_payment.strftime('%Y-%m-%d'),
                            'days_until': days_until,
                            'url': sub.url
                        }

                        # Send notification
                        NotificationManager.send_payment_reminder(sub.user_id, subscription_data)
                        notifications_sent += 1

                print(f"✅ Sent {notifications_sent} upcoming payment notifications")

            except Exception as e:
                print(f"❌ Error sending upcoming payment notifications: {e}")

    def send_overdue_notifications(self):
        """
        Send notifications for overdue payments

        Checks all active subscriptions with past payment dates
        """
        with self.app.app_context():
            try:
                today = datetime.now().date()

                # Get overdue subscriptions
                overdue_subscriptions = db.session.query(Subscription).filter(
                    Subscription.inactive == False,
                    Subscription.next_payment < today
                ).all()

                notifications_sent = 0

                for sub in overdue_subscriptions:
                    # Get user's currency
                    currency_symbol = '$'
                    if sub.currency:
                        currency_symbol = sub.currency.symbol

                    # Prepare subscription data
                    subscription_data = {
                        'name': sub.name,
                        'price': sub.price,
                        'currency_symbol': currency_symbol,
                        'next_payment': sub.next_payment.strftime('%Y-%m-%d'),
                        'url': sub.url
                    }

                    # Send notification
                    NotificationManager.send_overdue_reminder(sub.user_id, subscription_data)
                    notifications_sent += 1

                print(f"✅ Sent {notifications_sent} overdue payment notifications")

            except Exception as e:
                print(f"❌ Error sending overdue notifications: {e}")

    def send_cancellation_reminders(self):
        """
        Send reminders for subscriptions with upcoming cancellation dates

        Notifies users 7 days before cancellation date
        """
        with self.app.app_context():
            try:
                today = datetime.now().date()
                reminder_date = today + timedelta(days=7)

                # Get subscriptions with cancellation date in 7 days
                subscriptions = db.session.query(Subscription).filter(
                    Subscription.cancellation_date == reminder_date
                ).all()

                notifications_sent = 0

                for sub in subscriptions:
                    # Get user's currency
                    currency_symbol = '$'
                    if sub.currency:
                        currency_symbol = sub.currency.symbol

                    # Prepare subscription data
                    subscription_data = {
                        'name': sub.name,
                        'price': sub.price,
                        'currency_symbol': currency_symbol,
                        'cancellation_date': sub.cancellation_date.strftime('%Y-%m-%d'),
                        'url': sub.url
                    }

                    # Send notification
                    NotificationManager.send_cancellation_reminder(sub.user_id, subscription_data)
                    notifications_sent += 1

                print(f"✅ Sent {notifications_sent} cancellation reminder notifications")

            except Exception as e:
                print(f"❌ Error sending cancellation reminders: {e}")

    def update_currency_rates(self):
        """
        Update currency exchange rates from Fixer.io

        Requires FIXER_API_KEY environment variable
        """
        with self.app.app_context():
            try:
                import os
                api_key = os.getenv('FIXER_API_KEY')

                if not api_key:
                    print("⚠️  FIXER_API_KEY not set, skipping currency update")
                    return

                success = CurrencyConverter.update_exchange_rates(api_key)

                if success:
                    print("✅ Currency exchange rates updated successfully")
                else:
                    print("❌ Failed to update currency exchange rates")

            except Exception as e:
                print(f"❌ Error updating currency rates: {e}")

    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("✅ Notification scheduler stopped")
