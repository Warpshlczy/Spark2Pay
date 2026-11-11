"""
Base Notification Service
Abstract class for all notification channels
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from app import db
from app.models.notification import NotificationLog


class BaseNotificationService(ABC):
    """Base class for all notification services"""

    def __init__(self, user_id: int, config: Dict[str, Any]):
        """
        Initialize notification service

        Args:
            user_id: User ID
            config: Configuration dictionary for this notification channel
        """
        self.user_id = user_id
        self.config = config
        self.channel_name = self.__class__.__name__.replace('NotificationService', '').lower()

    @abstractmethod
    def send(self, title: str, message: str, subscription_data: Optional[Dict] = None) -> bool:
        """
        Send notification

        Args:
            title: Notification title
            message: Notification message body
            subscription_data: Optional subscription data for context

        Returns:
            True if sent successfully, False otherwise
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test notification channel configuration

        Returns:
            True if configuration is valid, False otherwise
        """
        pass

    def log_notification(self, success: bool, error_message: Optional[str] = None,
                         notification_type: str = 'manual', subscription_id: Optional[int] = None):
        """
        Log notification attempt

        Args:
            success: Whether notification was sent successfully
            error_message: Error message if failed
            notification_type: Type of notification (upcoming, overdue, cancellation, manual)
            subscription_id: Optional subscription ID
        """
        log = NotificationLog(
            user_id=self.user_id,
            channel=self.channel_name,
            notification_type=notification_type,
            status='sent' if success else 'failed',
            error_message=error_message,
            subscription_id=subscription_id
        )
        db.session.add(log)
        db.session.commit()

    def format_subscription_message(self, subscription_data: Dict, event_type: str) -> str:
        """
        Format subscription data into notification message

        Args:
            subscription_data: Subscription information
            event_type: Type of event (upcoming_payment, overdue, etc.)

        Returns:
            Formatted message string
        """
        name = subscription_data.get('name', 'Unknown')
        price = subscription_data.get('price', 0)
        currency = subscription_data.get('currency_symbol', '$')
        next_payment = subscription_data.get('next_payment', 'Unknown')

        if event_type == 'upcoming_payment':
            return f"""
Subscription Payment Reminder

Subscription: {name}
Amount: {currency}{price}
Payment Date: {next_payment}
Days Until Payment: {subscription_data.get('days_until', 'N/A')}

Manage your subscription at: {subscription_data.get('url', 'N/A')}
            """.strip()

        elif event_type == 'overdue':
            return f"""
Overdue Subscription Payment

Subscription: {name}
Amount: {currency}{price}
Due Date: {next_payment}

Please review and update your subscription.
            """.strip()

        elif event_type == 'cancellation_reminder':
            cancellation_date = subscription_data.get('cancellation_date', 'Unknown')
            return f"""
Subscription Cancellation Reminder

Subscription: {name}
Cancellation Date: {cancellation_date}

Your subscription will be cancelled soon. Please take necessary action if needed.
            """.strip()

        return f"Notification for {name}: {event_type}"

    def validate_config(self, required_fields: list) -> bool:
        """
        Validate that all required configuration fields are present

        Args:
            required_fields: List of required field names

        Returns:
            True if all required fields present, False otherwise
        """
        for field in required_fields:
            if field not in self.config or not self.config[field]:
                return False
        return True
