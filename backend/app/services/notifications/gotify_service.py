"""
Gotify Notification Service
Sends notifications via Gotify (self-hosted notification server)
"""
import requests
from typing import Dict, Optional
from app.services.notifications.base import BaseNotificationService


class GotifyNotificationService(BaseNotificationService):
    """Gotify self-hosted notification service"""

    def send(self, title: str, message: str, subscription_data: Optional[Dict] = None) -> bool:
        """
        Send Gotify notification

        Args:
            title: Notification title
            message: Notification message
            subscription_data: Optional subscription data

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Validate configuration
            if not self.validate_config(['server_url', 'app_token']):
                self.log_notification(False, "Missing Gotify server URL or app token")
                return False

            # Format message with subscription data if provided
            if subscription_data:
                event_type = subscription_data.get('event_type', 'notification')
                message = self.format_subscription_message(subscription_data, event_type)

            # Send notification via Gotify API
            server_url = self.config['server_url'].rstrip('/')
            api_url = f"{server_url}/message"

            payload = {
                'title': title,
                'message': message,
                'priority': self.config.get('priority', 5)  # 0-10
            }

            # Add extras for subscription data
            if subscription_data:
                payload['extras'] = {
                    'client::display': {
                        'contentType': 'text/markdown'
                    }
                }

            params = {
                'token': self.config['app_token']
            }

            response = requests.post(
                api_url,
                json=payload,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                self.log_notification(True)
                return True
            else:
                self.log_notification(False, f"Gotify API error: {response.status_code}")
                return False

        except requests.RequestException as e:
            self.log_notification(False, f"Gotify request error: {str(e)}")
            return False
        except Exception as e:
            self.log_notification(False, f"Gotify send error: {str(e)}")
            return False

    def test_connection(self) -> bool:
        """
        Test Gotify server connection and token

        Returns:
            True if server is accessible and token is valid, False otherwise
        """
        try:
            if not self.validate_config(['server_url', 'app_token']):
                return False

            # Test server health
            server_url = self.config['server_url'].rstrip('/')
            health_url = f"{server_url}/health"

            response = requests.get(health_url, timeout=10)
            if response.status_code != 200:
                return False

            # Send test message
            api_url = f"{server_url}/message"

            payload = {
                'title': 'Spark2Pay Test',
                'message': 'Spark2Pay notification test - connection successful! ✅',
                'priority': 5
            }

            params = {
                'token': self.config['app_token']
            }

            response = requests.post(
                api_url,
                json=payload,
                params=params,
                timeout=10
            )

            return response.status_code == 200

        except Exception:
            return False
