"""
User Model
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models import Base


class User(Base):
    """User model for authentication and profile"""

    __tablename__ = 'users'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Authentication
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)  # bcrypt hash
    email = Column(String(255), unique=True, nullable=False, index=True)
    email_verified = Column(Boolean, default=False)

    # Profile
    firstname = Column(String(100))
    avatar = Column(String(255))

    # Preferences
    main_currency = Column(Integer)  # FK to currencies (can't add FK here due to circular dependency)
    budget = Column(Float)

    # Security
    totp_secret = Column(String(255))
    totp_enabled = Column(Boolean, default=False)

    # Authorization
    is_admin = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    subscriptions = relationship('Subscription', back_populates='user', cascade='all, delete-orphan')
    currencies = relationship('Currency', back_populates='user', cascade='all, delete-orphan')
    categories = relationship('Category', back_populates='user', cascade='all, delete-orphan')
    household_members = relationship('HouseholdMember', back_populates='user', cascade='all, delete-orphan')
    payment_methods = relationship('PaymentMethod', back_populates='user', cascade='all, delete-orphan')
    ai_recommendations = relationship('AIRecommendation', back_populates='user', cascade='all, delete-orphan')
    ml_insights = relationship('MLInsight', back_populates='user', cascade='all, delete-orphan')
    receipts = relationship('Receipt', back_populates='user', cascade='all, delete-orphan')

    def to_dict(self):
        """Convert user to dictionary (excluding sensitive data)"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'firstname': self.firstname,
            'avatar': self.avatar,
            'main_currency': self.main_currency,
            'budget': self.budget,
            'is_admin': self.is_admin,
            'totp_enabled': self.totp_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<User {self.username}>'
