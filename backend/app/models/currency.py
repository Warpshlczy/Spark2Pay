"""
Currency Model
"""
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models import Base


class Currency(Base):
    """Currency model for multi-currency support"""

    __tablename__ = 'currencies'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Owner
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Currency Details
    name = Column(String(100), nullable=False)  # e.g., "US Dollar"
    code = Column(String(10), nullable=False)  # e.g., "USD"
    symbol = Column(String(10), nullable=False)  # e.g., "$"
    rate = Column(Float, nullable=False, default=1.0)  # Exchange rate to USD base

    # Timestamps
    last_updated = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship('User', back_populates='currencies')

    def to_dict(self):
        """Convert currency to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'symbol': self.symbol,
            'rate': self.rate,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

    def __repr__(self):
        return f'<Currency {self.code}>'
