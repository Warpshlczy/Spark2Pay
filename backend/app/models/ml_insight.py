"""
ML Insight Model
"""
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models import Base


class MLInsight(Base):
    """ML-powered insights (anomalies, predictions, patterns)"""

    __tablename__ = 'ml_insights'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Owner
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Insight Details
    insight_type = Column(String(50), nullable=False, index=True)  # anomaly, pattern, prediction, recommendation
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    data = Column(Text)  # JSON with insight details
    severity = Column(String(20))  # info, warning, critical

    # Status
    dismissed = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship('User', back_populates='ml_insights')

    def to_dict(self):
        """Convert ML insight to dictionary"""
        import json
        return {
            'id': self.id,
            'type': self.insight_type,
            'title': self.title,
            'description': self.description,
            'data': json.loads(self.data) if self.data else {},
            'severity': self.severity,
            'dismissed': self.dismissed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<MLInsight {self.title}>'
