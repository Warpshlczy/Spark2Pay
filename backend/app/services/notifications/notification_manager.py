"""
Notification Manager
Coordinates sending notifications across all configured channels
"""
from typing import Dict, List, Optional
from datetime import datetime
from app import db
from app.models.user import User
from app.models.notification import (
    NotificationSettings,
    EmailNotification,
    DiscordNotification,
    TelegramNotification,
    PushoverNotification
)
from app.services.notifications.email_service import EmailNotificationService
from app.services.notifications.discord_service import DiscordNotificationService
from app.services.notifications.telegram_service import TelegramNotificationService
from app.services.notifications.pushover_service import PushoverNotificationService
from app.services.notifications.pushplus_service import PushPlusNotificationService
from app.services.notifications.mattermost_service import MattermostNotificationService
from app.services.notifications.ntfy_service import NtfyNotificationService
from app.services.notifications.gotify_service import GotifyNotificationService
from app.services.notifications.webhook_service import WebhookNotificationService


class NotificationManager:
    """Manage and send notifications across all channels"""

    # Service class mapping
    SERVICE_MAP = {
        'email': EmailNotificationService,
        'discord': DiscordNotificationService,
        'telegram': TelegramNotificationService,
        'pushover': PushoverNotificationService,
        'pushplus': PushPlusNotificationService,
        'mattermost': MattermostNotificationService,
        'ntfy': NtfyNotificationService,
        'gotify': GotifyNotificationService,
        'webhook': WebhookNotificationService
    }

    @staticmethod
    def get_user_notification_config(user_id: int) -> Dict[str, Dict]:
        """
        Get notification configuration for user

        Args:
            user_id: User ID

        Returns:
            Dictionary mapping channel name to configuration
        """
        config = {}

        # Check notification settings to see which channels are enabled
        settings = db.session.query(NotificationSettings).filter_by(user_id=user_id).first()

        if not settings:
            return config

        # Email
        if settings.email_enabled:
            email_config = db.session.query(EmailNotification).filter_by(user_id=user_id).first()
            if email_config:
                config['email'] = {
                    'smtp_host': email_config.smtp_address,  # Map smtp_address to smtp_host for service
                    'smtp_port': email_config.smtp_port,
                    'smtp_username': email_config.smtp_username,
                    'smtp_password': email_config.smtp_password,
                    'from_email': email_config.from_email,
                    'to_email': email_config.to_email,
                    'use_tls': email_config.encryption == 'tls'
                }

        # Discord
        if settings.discord_enabled:
            discord_config = db.session.query(DiscordNotification).filter_by(user_id=user_id).first()
            if discord_config:
                config['discord'] = {
                    'webhook_url': discord_config.webhook_url
                }

        # Telegram
        if settings.telegram_enabled:
            telegram_config = db.session.query(TelegramNotification).filter_by(user_id=user_id).first()
            if telegram_config:
                config['telegram'] = {
                    'bot_token': telegram_config.bot_token,
                    'chat_id': telegram_config.chat_id
                }

        # Pushover
        if settings.pushover_enabled:
            pushover_config = db.session.query(PushoverNotification).filter_by(user_id=user_id).first()
            if pushover_config:
                config['pushover'] = {
                    'user_key': pushover_config.user_key,
                    'api_token': pushover_config.api_token,
                    'priority': pushover_config.priority,
                    'sound': pushover_config.sound
                }

        return config

    @staticmethod
    def send_notification(
        user_id: int,
        title: str,
        message: str,
        subscription_data: Optional[Dict] = None,
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Send notification to user across configured channels

        Args:
            user_id: User ID
            title: Notification title
            message: Notification message
            subscription_data: Optional subscription data for context
            channels: Optional list of specific channels to use (if None, use all enabled)

        Returns:
            Dictionary mapping channel name to success status
        """
        results = {}

        # Get user's notification configuration
        config = NotificationManager.get_user_notification_config(user_id)

        # Filter channels if specified
        if channels:
            config = {k: v for k, v in config.items() if k in channels}

        # Send to each configured channel
        for channel_name, channel_config in config.items():
            if channel_name in NotificationManager.SERVICE_MAP:
                try:
                    service_class = NotificationManager.SERVICE_MAP[channel_name]
                    service = service_class(user_id, channel_config)
                    success = service.send(title, message, subscription_data)
                    results[channel_name] = success
                except Exception as e:
                    print(f"Error sending {channel_name} notification: {e}")
                    results[channel_name] = False

        return results

    @staticmethod
    def test_channel(user_id: int, channel_name: str) -> bool:
        """
        Test a specific notification channel

        Args:
            user_id: User ID
            channel_name: Name of channel to test

        Returns:
            True if test successful, False otherwise
        """
        try:
            if channel_name not in NotificationManager.SERVICE_MAP:
                return False

            config = NotificationManager.get_user_notification_config(user_id)

            if channel_name not in config:
                return False

            service_class = NotificationManager.SERVICE_MAP[channel_name]
            service = service_class(user_id, config[channel_name])
            return service.test_connection()

        except Exception as e:
            print(f"Error testing {channel_name}: {e}")
            return False

    @staticmethod
    def send_payment_reminder(user_id: int, subscription_data: Dict) -> Dict[str, bool]:
        """
        Send payment reminder notification

        Args:
            user_id: User ID
            subscription_data: Subscription information

        Returns:
            Dictionary mapping channel name to success status
        """
        subscription_data['event_type'] = 'upcoming_payment'
        subscription_data['timestamp'] = datetime.now().isoformat()

        title = f"Payment Reminder: {subscription_data['name']}"
        message = f"Your subscription payment is due soon"

        return NotificationManager.send_notification(
            user_id,
            title,
            message,
            subscription_data
        )

    @staticmethod
    def send_overdue_reminder(user_id: int, subscription_data: Dict) -> Dict[str, bool]:
        """
        Send overdue payment notification

        Args:
            user_id: User ID
            subscription_data: Subscription information

        Returns:
            Dictionary mapping channel name to success status
        """
        subscription_data['event_type'] = 'overdue'
        subscription_data['timestamp'] = datetime.now().isoformat()

        title = f"Overdue Payment: {subscription_data['name']}"
        message = f"Your subscription payment is overdue"

        return NotificationManager.send_notification(
            user_id,
            title,
            message,
            subscription_data
        )

    @staticmethod
    def send_cancellation_reminder(user_id: int, subscription_data: Dict) -> Dict[str, bool]:
        """
        Send cancellation reminder notification

        Args:
            user_id: User ID
            subscription_data: Subscription information

        Returns:
            Dictionary mapping channel name to success status
        """
        subscription_data['event_type'] = 'cancellation_reminder'
        subscription_data['timestamp'] = datetime.now().isoformat()

        title = f"Cancellation Reminder: {subscription_data['name']}"
        message = f"Your subscription will be cancelled soon"

        return NotificationManager.send_notification(
            user_id,
            title,
            message,
            subscription_data
        )
