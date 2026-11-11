"""
Category Model
"""
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models import Base


class Category(Base):
    """Category model for organizing subscriptions"""

    __tablename__ = 'categories'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Owner
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Category Details
    name = Column(String(100), nullable=False)
    order = Column(Integer, default=0)  # For custom sorting

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship('User', back_populates='categories')

    def to_dict(self):
        """Convert category to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'order': self.order
        }

    def __repr__(self):
        return f'<Category {self.name}>'
