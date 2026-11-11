"""
Mattermost Notification Service
Sends notifications via Mattermost webhooks
"""
import requests
from typing import Dict, Optional
from app.services.notifications.base import BaseNotificationService


class MattermostNotificationService(BaseNotificationService):
    """Mattermost webhook notification service"""

    def send(self, title: str, message: str, subscription_data: Optional[Dict] = None) -> bool:
        """
        Send Mattermost notification via webhook

        Args:
            title: Notification title
            message: Notification message
            subscription_data: Optional subscription data

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Validate configuration
            if not self.validate_config(['webhook_url']):
                self.log_notification(False, "Missing Mattermost webhook URL")
                return False

            # Format message with subscription data if provided
            if subscription_data:
                event_type = subscription_data.get('event_type', 'notification')
                message = self.format_subscription_message(subscription_data, event_type)

            # Create Mattermost message with attachment
            payload = {
                'username': 'Spark2Pay Notifications',
                'icon_url': self.config.get('icon_url', ''),
                'text': f"**{title}**",
                'attachments': [{
                    'text': message,
                    'color': '#FF8C00'  # Orange color
                }]
            }

            # Add fields for subscription data
            if subscription_data:
                fields = []
                if 'name' in subscription_data:
                    fields.append({
                        'short': True,
                        'title': 'Subscription',
                        'value': subscription_data['name']
                    })
                if 'price' in subscription_data and 'currency_symbol' in subscription_data:
                    fields.append({
                        'short': True,
                        'title': 'Amount',
                        'value': f"{subscription_data['currency_symbol']}{subscription_data['price']}"
                    })
                if 'next_payment' in subscription_data:
                    fields.append({
                        'short': True,
                        'title': 'Payment Date',
                        'value': subscription_data['next_payment']
                    })

                if fields:
                    payload['attachments'][0]['fields'] = fields

            # Send webhook request
            response = requests.post(
                self.config['webhook_url'],
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                self.log_notification(True)
                return True
            else:
                self.log_notification(False, f"Mattermost API error: {response.status_code}")
                return False

        except requests.RequestException as e:
            self.log_notification(False, f"Mattermost request error: {str(e)}")
            return False
        except Exception as e:
            self.log_notification(False, f"Mattermost send error: {str(e)}")
            return False

    def test_connection(self) -> bool:
        """
        Test Mattermost webhook URL

        Returns:
            True if webhook is valid, False otherwise
        """
        try:
            if not self.validate_config(['webhook_url']):
                return False

            # Send test message
            payload = {
                'text': 'Spark2Pay notification test - connection successful! ✅',
                'username': 'Spark2Pay Notifications'
            }

            response = requests.post(
                self.config['webhook_url'],
                json=payload,
                timeout=10
            )

            return response.status_code == 200

        except Exception:
            return False
