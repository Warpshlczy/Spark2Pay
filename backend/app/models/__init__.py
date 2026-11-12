"""
Database Models
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import all models here for Alembic to discover
from app.models.user import User
from app.models.subscription import Subscription
from app.models.currency import Currency
from app.models.category import Category
from app.models.household import HouseholdMember
from app.models.payment_method import PaymentMethod
from app.models.notification import (
    NotificationSettings,
    EmailNotification,
    DiscordNotification,
    TelegramNotification,
    PushoverNotification,
    WebhookNotification,
    NotificationLog
)
from app.models.ai_recommendation import AIRecommendation
from app.models.ml_insight import MLInsight
from app.models.receipt import Receipt
from app.models.paypal_action import PayPalAction
from app.models.subscription_usage import SubscriptionUsage
from app.models.app_setting import AppSetting

__all__ = [
    'Base',
    'User',
    'Subscription',
    'Currency',
    'Category',
    'HouseholdMember',
    'PaymentMethod',
    'NotificationSettings',
    'EmailNotification',
    'DiscordNotification',
    'TelegramNotification',
    'PushoverNotification',
    'WebhookNotification',
    'NotificationLog',
    'AIRecommendation',
    'MLInsight',
    'Receipt',
    'PayPalAction',
    'SubscriptionUsage',
    'AppSetting'
]
