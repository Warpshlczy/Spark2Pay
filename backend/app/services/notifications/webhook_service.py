"""
Generic Webhook Notification Service
Sends notifications to any custom webhook endpoint
"""
import requests
from typing import Dict, Optional
from app.services.notifications.base import BaseNotificationService


class WebhookNotificationService(BaseNotificationService):
    """Generic webhook notification service"""

    def send(self, title: str, message: str, subscription_data: Optional[Dict] = None) -> bool:
        """
        Send webhook notification

        Args:
            title: Notification title
            message: Notification message
            subscription_data: Optional subscription data

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Validate configuration
            if not self.validate_config(['url']):
                self.log_notification(False, "Missing webhook URL")
                return False

            # Format message with subscription data if provided
            if subscription_data:
                event_type = subscription_data.get('event_type', 'notification')
                formatted_message = self.format_subscription_message(subscription_data, event_type)
            else:
                formatted_message = message

            # Prepare payload based on configured format
            payload_format = self.config.get('format', 'json')  # json or form

            if payload_format == 'json':
                payload = {
                    'title': title,
                    'message': formatted_message,
                    'timestamp': subscription_data.get('timestamp') if subscription_data else None,
                    'source': 'Spark2Pay'
                }

                # Add subscription data if available
                if subscription_data:
                    payload['subscription'] = subscription_data

                headers = {
                    'Content-Type': 'application/json'
                }

                # Add custom headers if configured
                if 'headers' in self.config:
                    headers.update(self.config['headers'])

                response = requests.post(
                    self.config['url'],
                    json=payload,
                    headers=headers,
                    timeout=10
                )

            else:  # form data
                data = {
                    'title': title,
                    'message': formatted_message,
                    'source': 'Spark2Pay'
                }

                headers = {}
                if 'headers' in self.config:
                    headers.update(self.config['headers'])

                response = requests.post(
                    self.config['url'],
                    data=data,
                    headers=headers,
                    timeout=10
                )

            # Check response
            success_codes = self.config.get('success_codes', [200, 201, 202, 204])

            if response.status_code in success_codes:
                self.log_notification(True)
                return True
            else:
                self.log_notification(False, f"Webhook error: {response.status_code}")
                return False

        except requests.RequestException as e:
            self.log_notification(False, f"Webhook request error: {str(e)}")
            return False
        except Exception as e:
            self.log_notification(False, f"Webhook send error: {str(e)}")
            return False

    def test_connection(self) -> bool:
        """
        Test webhook endpoint

        Returns:
            True if webhook is accessible, False otherwise
        """
        try:
            if not self.validate_config(['url']):
                return False

            # Send test message
            payload = {
                'title': 'Spark2Pay Test',
                'message': 'Spark2Pay notification test - connection successful! ✅',
                'source': 'Spark2Pay',
                'test': True
            }

            headers = {
                'Content-Type': 'application/json'
            }

            # Add custom headers if configured
            if 'headers' in self.config:
                headers.update(self.config['headers'])

            response = requests.post(
                self.config['url'],
                json=payload,
                headers=headers,
                timeout=10
            )

            success_codes = self.config.get('success_codes', [200, 201, 202, 204])
            return response.status_code in success_codes

        except Exception:
            return False
