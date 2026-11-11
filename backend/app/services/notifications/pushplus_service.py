"""
PushPlus Notification Service
Sends notifications via PushPlus API (Chinese push notification service)
"""
import requests
from typing import Dict, Optional
from app.services.notifications.base import BaseNotificationService


class PushPlusNotificationService(BaseNotificationService):
    """PushPlus notification service"""

    def send(self, title: str, message: str, subscription_data: Optional[Dict] = None) -> bool:
        """
        Send PushPlus notification

        Args:
            title: Notification title
            message: Notification message
            subscription_data: Optional subscription data

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Validate configuration
            if not self.validate_config(['token']):
                self.log_notification(False, "Missing PushPlus token")
                return False

            # Format message with subscription data if provided
            if subscription_data:
                event_type = subscription_data.get('event_type', 'notification')
                message = self.format_subscription_message(subscription_data, event_type)

            # Send notification via PushPlus API
            api_url = "http://www.pushplus.plus/send"

            payload = {
                'token': self.config['token'],
                'title': title,
                'content': message,
                'template': self.config.get('template', 'html')
            }

            # Add topic if configured (for group notifications)
            if 'topic' in self.config:
                payload['topic'] = self.config['topic']

            response = requests.post(api_url, json=payload, timeout=10)
            data = response.json()

            if data.get('code') == 200:
                self.log_notification(True)
                return True
            else:
                error_msg = data.get('msg', 'Unknown error')
                self.log_notification(False, f"PushPlus API error: {error_msg}")
                return False

        except requests.RequestException as e:
            self.log_notification(False, f"PushPlus request error: {str(e)}")
            return False
        except Exception as e:
            self.log_notification(False, f"PushPlus send error: {str(e)}")
            return False

    def test_connection(self) -> bool:
        """
        Test PushPlus configuration

        Returns:
            True if token is valid, False otherwise
        """
        try:
            if not self.validate_config(['token']):
                return False

            # Send test message
            api_url = "http://www.pushplus.plus/send"

            payload = {
                'token': self.config['token'],
                'title': 'Spark2Pay Test',
                'content': 'Spark2Pay notification test - connection successful! ✅',
                'template': 'txt'
            }

            response = requests.post(api_url, json=payload, timeout=10)
            data = response.json()

            return data.get('code') == 200

        except Exception:
            return False
