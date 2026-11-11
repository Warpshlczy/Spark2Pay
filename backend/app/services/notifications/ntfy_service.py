"""
Ntfy Notification Service
Sends notifications via Ntfy.sh (simple pub-sub notifications)
"""
import requests
from typing import Dict, Optional
from app.services.notifications.base import BaseNotificationService


class NtfyNotificationService(BaseNotificationService):
    """Ntfy.sh notification service"""

    def send(self, title: str, message: str, subscription_data: Optional[Dict] = None) -> bool:
        """
        Send Ntfy notification

        Args:
            title: Notification title
            message: Notification message
            subscription_data: Optional subscription data

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Validate configuration
            if not self.validate_config(['topic']):
                self.log_notification(False, "Missing Ntfy topic")
                return False

            # Format message with subscription data if provided
            if subscription_data:
                event_type = subscription_data.get('event_type', 'notification')
                message = self.format_subscription_message(subscription_data, event_type)

            # Get server URL (default to ntfy.sh)
            server_url = self.config.get('server_url', 'https://ntfy.sh')
            topic = self.config['topic']
            api_url = f"{server_url}/{topic}"

            # Prepare headers
            headers = {
                'Title': title,
                'Priority': self.config.get('priority', 'default'),  # max, high, default, low, min
                'Tags': self.config.get('tags', 'money_with_wings,calendar')
            }

            # Add authentication if configured
            if 'username' in self.config and 'password' in self.config:
                auth = (self.config['username'], self.config['password'])
            else:
                auth = None

            # Add click action if URL available
            if subscription_data and 'url' in subscription_data:
                headers['Click'] = subscription_data['url']

            # Send notification
            response = requests.post(
                api_url,
                data=message.encode('utf-8'),
                headers=headers,
                auth=auth,
                timeout=10
            )

            if response.status_code == 200:
                self.log_notification(True)
                return True
            else:
                self.log_notification(False, f"Ntfy API error: {response.status_code}")
                return False

        except requests.RequestException as e:
            self.log_notification(False, f"Ntfy request error: {str(e)}")
            return False
        except Exception as e:
            self.log_notification(False, f"Ntfy send error: {str(e)}")
            return False

    def test_connection(self) -> bool:
        """
        Test Ntfy configuration

        Returns:
            True if topic is accessible, False otherwise
        """
        try:
            if not self.validate_config(['topic']):
                return False

            # Send test message
            server_url = self.config.get('server_url', 'https://ntfy.sh')
            topic = self.config['topic']
            api_url = f"{server_url}/{topic}"

            headers = {
                'Title': 'Spark2Pay Test',
                'Tags': 'white_check_mark'
            }

            # Add authentication if configured
            if 'username' in self.config and 'password' in self.config:
                auth = (self.config['username'], self.config['password'])
            else:
                auth = None

            response = requests.post(
                api_url,
                data='Spark2Pay notification test - connection successful! ✅',
                headers=headers,
                auth=auth,
                timeout=10
            )

            return response.status_code == 200

        except Exception:
            return False
