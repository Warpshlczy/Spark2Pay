"""
PayPal Action Model
Audit trail for every PayPal execution attempt (the "last mile" ledger)
"""
import json
from sqlalchemy import Column, Integer, String, Float, Boolean, TIMESTAMP, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models import Base


class PayPalAction(Base):
    """Audit record of a PayPal-backed execution (cancel, suspend, activate, pay)"""

    __tablename__ = 'paypal_actions'

    # Lifecycle: pending_approval -> executing -> completed | failed | rejected
    STATUS_PENDING_APPROVAL = 'pending_approval'
    STATUS_EXECUTING = 'executing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_REJECTED = 'rejected'

    ACTION_CANCEL = 'cancel'
    ACTION_SUSPEND = 'suspend'
    ACTION_ACTIVATE = 'activate'
    ACTION_PAY = 'pay'
    ALLOWED_ACTIONS = (ACTION_CANCEL, ACTION_SUSPEND, ACTION_ACTIVATE, ACTION_PAY)

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Ownership
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id', ondelete='SET NULL'), index=True)

    # Action
    action_type = Column(String(20), nullable=False)
    status = Column(String(30), nullable=False, default=STATUS_PENDING_APPROVAL, index=True)
    reason = Column(String(500))

    # Money (for pay actions and savings reporting)
    amount = Column(Float)
    currency = Column(String(10))
    estimated_monthly_savings = Column(Float)

    # PayPal references
    paypal_order_id = Column(String(64), index=True)
    paypal_capture_id = Column(String(64))
    paypal_subscription_id = Column(String(64), index=True)

    # Mode this action ran in ('sandbox' | 'simulation') - part of the audit story
    paypal_mode = Column(String(20), nullable=False, default='simulation')

    # Free-form context: subscription snapshot, LLM proposal origin, webhook events
    payload = Column(Text)

    error = Column(Text)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    executed_at = Column(TIMESTAMP)

    # Relationships
    user = relationship('User', viewonly=True)
    subscription = relationship('Subscription', viewonly=True)

    def set_payload(self, data):
        self.payload = json.dumps(data, default=str)

    def get_payload(self):
        return json.loads(self.payload) if self.payload else {}

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'subscription_id': self.subscription_id,
            'subscription_name': (self.payload_json_name() or
                                  (self.subscription.name if self.subscription else None)),
            'action_type': self.action_type,
            'status': self.status,
            'reason': self.reason,
            'amount': self.amount,
            'currency': self.currency,
            'estimated_monthly_savings': self.estimated_monthly_savings,
            'paypal_order_id': self.paypal_order_id,
            'paypal_capture_id': self.paypal_capture_id,
            'paypal_subscription_id': self.paypal_subscription_id,
            'paypal_mode': self.paypal_mode,
            'payload': self.get_payload(),
            'error': self.error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None
        }

    def payload_json_name(self):
        payload = self.get_payload()
        return payload.get('subscription_name')

    def __repr__(self):
        return f'<PayPalAction {self.id} {self.action_type} {self.status}>'
