"""
Email Notification Service
Sends notifications via SMTP
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from app.services.notifications.base import BaseNotificationService


class EmailNotificationService(BaseNotificationService):
    """Email notification service using SMTP"""

    def send(self, title: str, message: str, subscription_data: Optional[Dict] = None) -> bool:
        """
        Send email notification

        Args:
            title: Email subject
            message: Email body
            subscription_data: Optional subscription data

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Validate configuration
            required_fields = ['smtp_host', 'smtp_port', 'from_email', 'to_email']
            if not self.validate_config(required_fields):
                self.log_notification(False, "Missing required SMTP configuration")
                return False

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = title
            msg['From'] = self.config['from_email']
            msg['To'] = self.config['to_email']

            # Format message with subscription data if provided
            if subscription_data:
                event_type = subscription_data.get('event_type', 'notification')
                message = self.format_subscription_message(subscription_data, event_type)

            # Create text and HTML parts
            text_part = MIMEText(message, 'plain')
            html_message = message.replace('\n', '<br>')
            html_part = MIMEText(f'<html><body>{html_message}</body></html>', 'html')

            msg.attach(text_part)
            msg.attach(html_part)

            # Connect to SMTP server
            smtp_host = self.config['smtp_host']
            smtp_port = int(self.config['smtp_port'])
            use_tls = self.config.get('use_tls', True)

            if use_tls:
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)

            # Authenticate if credentials provided
            if 'smtp_username' in self.config and 'smtp_password' in self.config:
                server.login(self.config['smtp_username'], self.config['smtp_password'])

            # Send email
            server.send_message(msg)
            server.quit()

            self.log_notification(True)
            return True

        except smtplib.SMTPException as e:
            self.log_notification(False, f"SMTP error: {str(e)}")
            return False
        except Exception as e:
            self.log_notification(False, f"Email send error: {str(e)}")
            return False

    def test_connection(self) -> bool:
        """
        Test SMTP connection and authentication

        Returns:
            True if connection successful, False otherwise
        """
        try:
            required_fields = ['smtp_host', 'smtp_port', 'from_email']
            if not self.validate_config(required_fields):
                return False

            smtp_host = self.config['smtp_host']
            smtp_port = int(self.config['smtp_port'])
            use_tls = self.config.get('use_tls', True)

            if use_tls:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)

            # Test authentication if credentials provided
            if 'smtp_username' in self.config and 'smtp_password' in self.config:
                server.login(self.config['smtp_username'], self.config['smtp_password'])

            server.quit()
            return True

        except Exception:
            return False
