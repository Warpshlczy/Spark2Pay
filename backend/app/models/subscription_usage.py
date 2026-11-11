"""
Subscription Usage Model
Tracks how much a subscription is actually used - fuel for AI savings advice
"""
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models import Base


class SubscriptionUsage(Base):
    """Usage telemetry for one subscription (one row per subscription)"""

    __tablename__ = 'subscription_usage'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Owner subscription (1:1)
    subscription_id = Column(
        Integer, ForeignKey('subscriptions.id', ondelete='CASCADE'),
        nullable=False, unique=True, index=True
    )

    # Usage signals
    last_used_at = Column(TIMESTAMP)          # last time the service was opened
    usage_count_30d = Column(Integer, default=0)  # opens in the last 30 days
    notes = Column(String(255))

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    subscription = relationship('Subscription', viewonly=True)

    def to_dict(self):
        return {
            'id': self.id,
            'subscription_id': self.subscription_id,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'usage_count_30d': self.usage_count_30d or 0,
            'notes': self.notes
        }

    def __repr__(self):
        return f'<SubscriptionUsage sub={self.subscription_id} 30d={self.usage_count_30d}>'
