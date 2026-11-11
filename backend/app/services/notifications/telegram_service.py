"""
Telegram Notification Service
Sends notifications via Telegram Bot API
"""
import requests
from typing import Dict, Optional
from app.services.notifications.base import BaseNotificationService


class TelegramNotificationService(BaseNotificationService):
    """Telegram Bot API notification service"""

    def send(self, title: str, message: str, subscription_data: Optional[Dict] = None) -> bool:
        """
        Send Telegram notification

        Args:
            title: Notification title
            message: Notification message
            subscription_data: Optional subscription data

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Validate configuration
            if not self.validate_config(['bot_token', 'chat_id']):
                self.log_notification(False, "Missing Telegram bot token or chat ID")
                return False

            # Format message with subscription data if provided
            if subscription_data:
                event_type = subscription_data.get('event_type', 'notification')
                message = self.format_subscription_message(subscription_data, event_type)

            # Format message in Markdown
            telegram_message = f"*{title}*\n\n{message}"

            # Send message via Telegram Bot API
            bot_token = self.config['bot_token']
            chat_id = self.config['chat_id']
            api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            payload = {
                'chat_id': chat_id,
                'text': telegram_message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }

            response = requests.post(api_url, json=payload, timeout=10)
            data = response.json()

            if data.get('ok'):
                self.log_notification(True)
                return True
            else:
                error_msg = data.get('description', 'Unknown error')
                self.log_notification(False, f"Telegram API error: {error_msg}")
                return False

        except requests.RequestException as e:
            self.log_notification(False, f"Telegram request error: {str(e)}")
            return False
        except Exception as e:
            self.log_notification(False, f"Telegram send error: {str(e)}")
            return False

    def test_connection(self) -> bool:
        """
        Test Telegram bot configuration

        Returns:
            True if bot token and chat ID are valid, False otherwise
        """
        try:
            if not self.validate_config(['bot_token', 'chat_id']):
                return False

            # Test bot token by getting bot info
            bot_token = self.config['bot_token']
            api_url = f"https://api.telegram.org/bot{bot_token}/getMe"

            response = requests.get(api_url, timeout=10)
            data = response.json()

            if not data.get('ok'):
                return False

            # Test sending a message to chat
            chat_id = self.config['chat_id']
            send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            payload = {
                'chat_id': chat_id,
                'text': 'Spark2Pay notification test - connection successful! ✅'
            }

            response = requests.post(send_url, json=payload, timeout=10)
            data = response.json()

            return data.get('ok', False)

        except Exception:
            return False
