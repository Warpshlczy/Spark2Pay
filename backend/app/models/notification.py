"""
Notification Models
"""
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models import Base


class NotificationSettings(Base):
    """Notification settings model"""

    __tablename__ = 'notification_settings'

    # Primary Key (also FK)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)

    # General Settings
    days_before = Column(Integer, default=7)

    # Channel Toggles
    email_enabled = Column(Boolean, default=False)
    discord_enabled = Column(Boolean, default=False)
    telegram_enabled = Column(Boolean, default=False)
    pushover_enabled = Column(Boolean, default=False)
    pushplus_enabled = Column(Boolean, default=False)
    mattermost_enabled = Column(Boolean, default=False)
    ntfy_enabled = Column(Boolean, default=False)
    gotify_enabled = Column(Boolean, default=False)
    webhook_enabled = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'days_before': self.days_before,
            'email_enabled': self.email_enabled,
            'discord_enabled': self.discord_enabled,
            'telegram_enabled': self.telegram_enabled,
            'pushover_enabled': self.pushover_enabled,
            'pushplus_enabled': self.pushplus_enabled,
            'mattermost_enabled': self.mattermost_enabled,
            'ntfy_enabled': self.ntfy_enabled,
            'gotify_enabled': self.gotify_enabled,
            'webhook_enabled': self.webhook_enabled
        }


class EmailNotification(Base):
    """Email notification configuration"""

    __tablename__ = 'email_notifications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    smtp_address = Column(String(255), nullable=False)  # SMTP server address
    smtp_port = Column(Integer, nullable=False, default=587)
    smtp_username = Column(String(255))
    smtp_password = Column(String(255))  # Should be encrypted
    from_email = Column(String(255), nullable=False)
    to_email = Column(String(255), nullable=False)  # Recipient email
    encryption = Column(String(20), default='tls')  # tls, ssl, or none

    created_at = Column(TIMESTAMP, server_default=func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'smtp_address': self.smtp_address,
            'smtp_port': self.smtp_port,
            'smtp_username': self.smtp_username,
            'from_email': self.from_email,
            'to_email': self.to_email,
            'encryption': self.encryption
        }


class DiscordNotification(Base):
    """Discord notification configuration"""

    __tablename__ = 'discord_notifications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    webhook_url = Column(String(500), nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'webhook_url': self.webhook_url
        }


class TelegramNotification(Base):
    """Telegram notification configuration"""

    __tablename__ = 'telegram_notifications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    bot_token = Column(String(255), nullable=False)
    chat_id = Column(String(255), nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'bot_token': self.bot_token,
            'chat_id': self.chat_id
        }


class PushoverNotification(Base):
    """Pushover notification configuration"""

    __tablename__ = 'pushover_notifications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    user_key = Column(String(255), nullable=False)
    api_token = Column(String(255), nullable=False)
    priority = Column(Integer, default=0)  # -2 to 2
    sound = Column(String(50), default='pushover')  # pushover, bike, bugle, etc.

    created_at = Column(TIMESTAMP, server_default=func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_key': self.user_key,
            'api_token': self.api_token,
            'priority': self.priority,
            'sound': self.sound
        }


class WebhookNotification(Base):
    """Generic webhook notification configuration"""

    __tablename__ = 'webhook_notifications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    webhook_url = Column(String(500), nullable=False)
    payload_template = Column(Text)  # JSON template
    headers = Column(Text)  # JSON object
    method = Column(String(10), default='POST')

    created_at = Column(TIMESTAMP, server_default=func.now())


class NotificationLog(Base):
    """Notification log for tracking sent notifications"""

    __tablename__ = 'notification_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id', ondelete='CASCADE'))

    channel = Column(String(50), nullable=False)  # email, discord, etc.
    notification_type = Column(String(50), nullable=False)  # upcoming, cancellation, overdue
    status = Column(String(20), nullable=False)  # sent, failed
    error_message = Column(Text)

    sent_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'subscription_id': self.subscription_id,
            'channel': self.channel,
            'notification_type': self.notification_type,
            'status': self.status,
            'error_message': self.error_message,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None
        }
