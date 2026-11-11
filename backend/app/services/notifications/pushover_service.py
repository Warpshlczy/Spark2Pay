"""
Pushover Notification Service
Sends notifications via Pushover API
"""
import requests
from typing import Dict, Optional
from app.services.notifications.base import BaseNotificationService


class PushoverNotificationService(BaseNotificationService):
    """Pushover push notification service"""

    def send(self, title: str, message: str, subscription_data: Optional[Dict] = None) -> bool:
        """
        Send Pushover notification

        Args:
            title: Notification title
            message: Notification message
            subscription_data: Optional subscription data

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Validate configuration
            if not self.validate_config(['user_key', 'api_token']):
                self.log_notification(False, "Missing Pushover user key or API token")
                return False

            # Format message with subscription data if provided
            if subscription_data:
                event_type = subscription_data.get('event_type', 'notification')
                message = self.format_subscription_message(subscription_data, event_type)

            # Send notification via Pushover API
            api_url = "https://api.pushover.net/1/messages.json"

            payload = {
                'token': self.config['api_token'],
                'user': self.config['user_key'],
                'title': title,
                'message': message,
                'priority': self.config.get('priority', 0),  # -2 to 2
                'sound': self.config.get('sound', 'pushover')
            }

            # Add URL if available in subscription data
            if subscription_data and 'url' in subscription_data:
                payload['url'] = subscription_data['url']
                payload['url_title'] = 'View Subscription'

            response = requests.post(api_url, data=payload, timeout=10)
            data = response.json()

            if data.get('status') == 1:
                self.log_notification(True)
                return True
            else:
                errors = data.get('errors', ['Unknown error'])
                self.log_notification(False, f"Pushover API error: {', '.join(errors)}")
                return False

        except requests.RequestException as e:
            self.log_notification(False, f"Pushover request error: {str(e)}")
            return False
        except Exception as e:
            self.log_notification(False, f"Pushover send error: {str(e)}")
            return False

    def test_connection(self) -> bool:
        """
        Test Pushover configuration

        Returns:
            True if API token and user key are valid, False otherwise
        """
        try:
            if not self.validate_config(['user_key', 'api_token']):
                return False

            # Validate user key
            api_url = "https://api.pushover.net/1/users/validate.json"

            payload = {
                'token': self.config['api_token'],
                'user': self.config['user_key']
            }

            response = requests.post(api_url, data=payload, timeout=10)
            data = response.json()

            return data.get('status') == 1

        except Exception:
            return False
