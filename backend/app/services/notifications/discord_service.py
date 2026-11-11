"""
Discord Notification Service
Sends notifications via Discord webhooks
"""
import requests
from typing import Dict, Optional
from app.services.notifications.base import BaseNotificationService


class DiscordNotificationService(BaseNotificationService):
    """Discord webhook notification service"""

    def send(self, title: str, message: str, subscription_data: Optional[Dict] = None) -> bool:
        """
        Send Discord notification via webhook

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
                self.log_notification(False, "Missing Discord webhook URL")
                return False

            # Format message with subscription data if provided
            if subscription_data:
                event_type = subscription_data.get('event_type', 'notification')
                message = self.format_subscription_message(subscription_data, event_type)

            # Create Discord embed
            embed = {
                'title': title,
                'description': message,
                'color': 16753920,  # Orange color (#FF8C00)
                'timestamp': subscription_data.get('timestamp') if subscription_data else None
            }

            # Add subscription-specific fields
            if subscription_data:
                embed['fields'] = []
                if 'name' in subscription_data:
                    embed['fields'].append({
                        'name': 'Subscription',
                        'value': subscription_data['name'],
                        'inline': True
                    })
                if 'price' in subscription_data and 'currency_symbol' in subscription_data:
                    embed['fields'].append({
                        'name': 'Amount',
                        'value': f"{subscription_data['currency_symbol']}{subscription_data['price']}",
                        'inline': True
                    })
                if 'next_payment' in subscription_data:
                    embed['fields'].append({
                        'name': 'Payment Date',
                        'value': subscription_data['next_payment'],
                        'inline': True
                    })

            # Send webhook request
            webhook_url = self.config['webhook_url']
            payload = {
                'embeds': [embed],
                'username': 'Spark2Pay Notifications'
            }

            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 204]:
                self.log_notification(True)
                return True
            else:
                self.log_notification(False, f"Discord API error: {response.status_code}")
                return False

        except requests.RequestException as e:
            self.log_notification(False, f"Discord request error: {str(e)}")
            return False
        except Exception as e:
            self.log_notification(False, f"Discord send error: {str(e)}")
            return False

    def test_connection(self) -> bool:
        """
        Test Discord webhook URL

        Returns:
            True if webhook is valid, False otherwise
        """
        try:
            if not self.validate_config(['webhook_url']):
                return False

            # Send test message
            payload = {
                'content': 'Spark2Pay notification test - connection successful! ✅',
                'username': 'Spark2Pay Notifications'
            }

            response = requests.post(
                self.config['webhook_url'],
                json=payload,
                timeout=10
            )

            return response.status_code in [200, 204]

        except Exception:
            return False
