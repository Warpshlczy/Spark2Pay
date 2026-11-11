"""
AI Recommendation Model
"""
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models import Base


class AIRecommendation(Base):
    """AI-powered cost optimization recommendations"""

    __tablename__ = 'ai_recommendations'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Owner
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Recommendation Details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    savings = Column(String(50))  # e.g., "$15.00/month"
    recommendation_type = Column(String(50))  # duplicate, alternative, bundle, cancel, optimize
    related_subscription_ids = Column(Text)  # JSON array

    # Status
    dismissed = Column(Boolean, default=False, index=True)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship('User', back_populates='ai_recommendations')

    def to_dict(self):
        """Convert AI recommendation to dictionary"""
        import json
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'savings': self.savings,
            'type': self.recommendation_type,
            'related_subscriptions': json.loads(self.related_subscription_ids) if self.related_subscription_ids else [],
            'dismissed': self.dismissed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<AIRecommendation {self.title}>'
