"""
Receipt Model
"""
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models import Base


class Receipt(Base):
    """Receipt model for OCR-processed receipts"""

    __tablename__ = 'receipts'

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Owner
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False)

    # Receipt File
    filename = Column(String(255), nullable=False)  # Original file

    # OCR Results
    extracted_text = Column(Text)  # Full OCR text
    extracted_data = Column(Text)  # JSON of parsed fields
    confidence_score = Column(Float)
    ocr_provider = Column(String(50))  # tesseract or google_vision

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship('User', back_populates='receipts')
    subscription = relationship('Subscription', back_populates='receipts')

    def to_dict(self):
        """Convert receipt to dictionary"""
        import json
        return {
            'id': self.id,
            'subscription_id': self.subscription_id,
            'filename': self.filename,
            'extracted_text': self.extracted_text,
            'extracted_data': json.loads(self.extracted_data) if self.extracted_data else {},
            'confidence_score': self.confidence_score,
            'ocr_provider': self.ocr_provider,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Receipt {self.filename}>'
