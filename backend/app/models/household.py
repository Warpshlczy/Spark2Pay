"""
Household Member Model
"""
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models import Base


class HouseholdMember(Base):
    """Household member model for multi-member tracking"""

    __tablename__ = 'household'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Owner
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Member Details
    name = Column(String(100), nullable=False)
    email = Column(String(255))
    avatar = Column(String(255))

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship('User', back_populates='household_members')

    def to_dict(self):
        """Convert household member to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'avatar': self.avatar
        }

    def __repr__(self):
        return f'<HouseholdMember {self.name}>'
