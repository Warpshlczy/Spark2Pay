"""
Subscription Model
"""
from sqlalchemy import Column, Integer, String, Float, Date, Boolean, TIMESTAMP, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models import Base


class Subscription(Base):
    """Subscription model for tracking recurring expenses"""

    __tablename__ = 'subscriptions'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Owner
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Basic Info
    name = Column(String(255), nullable=False)
    logo = Column(String(255))
    url = Column(String(500))
    notes = Column(Text)

    # Pricing
    price = Column(Float, nullable=False)
    currency_id = Column(Integer, ForeignKey('currencies.id'), nullable=False)

    # Billing Cycle
    # cycle: 1=days, 2=weeks, 3=months, 4=years
    cycle = Column(Integer, nullable=False)
    frequency = Column(Integer, nullable=False, default=1)  # every N cycles
    next_payment = Column(Date)
    auto_renew = Column(Boolean, default=True)

    # Organization
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='SET NULL'))
    payer_user_id = Column(Integer, ForeignKey('household.id', ondelete='SET NULL'))
    payment_method_id = Column(Integer, ForeignKey('payment_methods.id', ondelete='SET NULL'))

    # Status
    inactive = Column(Boolean, default=False, index=True)
    cancellation_date = Column(Date)
    replacement_subscription_id = Column(Integer, ForeignKey('subscriptions.id'))

    # PayPal linkage (set when this subscription is billed through PayPal
    # Subscriptions; NULL means it is paid directly by card and cannot be
    # managed via the PayPal execution layer)
    paypal_subscription_id = Column(String(64), index=True)

    # Notifications
    notify_days_before = Column(Integer, default=7)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship('User', back_populates='subscriptions')
    currency = relationship('Currency')
    category = relationship('Category')
    payer = relationship('HouseholdMember')
    payment_method = relationship('PaymentMethod')
    receipts = relationship('Receipt', back_populates='subscription', cascade='all, delete-orphan')

    def to_dict(self):
        """Convert subscription to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'currency': self.currency.to_dict() if self.currency else None,
            'cycle': self.cycle,
            'frequency': self.frequency,
            'next_payment': self.next_payment.isoformat() if self.next_payment else None,
            'auto_renew': self.auto_renew,
            'logo': self.logo,
            'url': self.url,
            'notes': self.notes,
            'category': self.category.to_dict() if self.category else None,
            'payer': self.payer.to_dict() if self.payer else None,
            'payment_method': self.payment_method.to_dict() if self.payment_method else None,
            'inactive': self.inactive,
            'cancellation_date': self.cancellation_date.isoformat() if self.cancellation_date else None,
            'paypal_subscription_id': self.paypal_subscription_id,
            'notify_days_before': self.notify_days_before,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Subscription {self.name}>'
