"""
Payment Method Model
"""
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models import Base


class PaymentMethod(Base):
    """Payment method model for tracking payment types"""

    __tablename__ = 'payment_methods'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Owner
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Payment Method Details
    name = Column(String(100), nullable=False)
    icon = Column(String(255))
    order = Column(Integer, default=0)  # For custom sorting

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship('User', back_populates='payment_methods')

    def to_dict(self):
        """Convert payment method to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'order': self.order
        }

    def __repr__(self):
        return f'<PaymentMethod {self.name}>'
